import logging
from typing import Optional, Dict, Any, Tuple
from database import (
    get_db, get_product, get_settings,
    get_customer_completed_orders_count, get_customer_active_pending_order
)

logger = logging.getLogger("glowmint.pricing")

def calculate_order_pricing(
    quantity: int,
    coupon_code: Optional[str] = None,
    customer_phone: Optional[str] = None,
    customer_email: Optional[str] = None,
    check_concurrent_pending: bool = False
) -> Dict[str, Any]:
    """
    Server-side authoritative pricing and coupon calculation.
    Enforces coupon eligibility, caps, min order value, order history, and shipping rules.
    """
    product = get_product()
    if not product:
        raise ValueError("Product not found or currently unavailable.")

    settings = get_settings()
    max_items = int(settings.get("max_items_per_order", 5))

    if not isinstance(quantity, int) or quantity < 1 or quantity > max_items:
        raise ValueError(f"Quantity must be an integer between 1 and {max_items}.")

    unit_price = float(product["regular_price"])
    reference_price = float(product.get("reference_price", unit_price))
    subtotal = round(unit_price * quantity, 2)

    discount_amount = 0.0
    applied_coupon: Optional[str] = None
    coupon_message: Optional[str] = None
    coupon_valid = False

    cleaned_code = coupon_code.strip().upper() if coupon_code else None

    if cleaned_code:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT code, discount_percent, max_discount, min_order_val, required_order_number, is_active, description
                FROM coupons
                WHERE UPPER(code) = ?
            """, (cleaned_code,))
            row = cursor.fetchone()

            if not row:
                coupon_message = f"Coupon '{cleaned_code}' is invalid or does not exist."
            elif not row["is_active"]:
                coupon_message = f"Coupon '{cleaned_code}' has expired or is currently inactive."
            elif subtotal < float(row["min_order_val"]):
                coupon_message = f"Coupon '{cleaned_code}' requires a minimum order value of ₹{row['min_order_val']:.0f}."
            else:
                req_order = int(row["required_order_number"])
                # Customer history check requires phone or email
                if req_order in (1, 2, 3):
                    if not customer_phone and not customer_email:
                        if req_order == 1:
                            coupon_valid = True
                            coupon_message = "FIRST50 Applied! 50% discount on your first order."
                        else:
                            coupon_message = f"Please enter your phone number or email to verify eligibility for '{cleaned_code}'."
                    else:
                        prior_orders = get_customer_completed_orders_count(
                            customer_phone or "",
                            customer_email or ""
                        )

                        # Concurrency check if placing an order
                        if check_concurrent_pending and req_order == 1:
                            active_pending = get_customer_active_pending_order(
                                customer_phone or "",
                                customer_email or "",
                                coupon_code=cleaned_code
                            )
                            if active_pending:
                                coupon_message = f"An active checkout session ({active_pending['id']}) already exists for this number. Please complete or wait a few minutes."
                                prior_orders = 999  # Flag to block duplicate simultaneous coupon usage

                        if req_order == 1:
                            if prior_orders == 0:
                                coupon_valid = True
                            elif coupon_message is None:
                                coupon_message = f"FIRST50 is reserved exclusively for first-time customers. We found {prior_orders} previous completed order(s) for this account."
                        elif req_order == 2:
                            if prior_orders == 1:
                                coupon_valid = True
                            else:
                                coupon_message = f"SECOND20 is valid exclusively on your 2nd completed order (current completed orders: {prior_orders})."
                        elif req_order == 3:
                            if prior_orders == 2:
                                coupon_valid = True
                            else:
                                coupon_message = f"THIRD10 is valid exclusively on your 3rd completed order (current completed orders: {prior_orders})."
                else:
                    coupon_valid = True

                if coupon_valid:
                    pct = float(row["discount_percent"])
                    max_cap = float(row["max_discount"])
                    calc_discount = round(subtotal * (pct / 100.0), 2)
                    discount_amount = min(calc_discount, max_cap)
                    applied_coupon = row["code"]
                    coupon_message = f"Success! {row['code']} applied — saved ₹{discount_amount:.2f} ({int(pct)}% off)."

    # Shipping calculation
    base_shipping_fee = float(settings.get("shipping_fee", 0.0))
    free_shipping_thresh = float(settings.get("free_shipping_threshold", 0.0))

    payable_before_shipping = subtotal - discount_amount
    if free_shipping_thresh <= 0.0 or payable_before_shipping >= free_shipping_thresh:
        shipping_fee = 0.0
    else:
        shipping_fee = base_shipping_fee

    total_amount = round(payable_before_shipping + shipping_fee, 2)

    return {
        "product_id": product["id"],
        "product_title": product["title"],
        "unit_price": unit_price,
        "reference_price": reference_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "coupon_code": applied_coupon,
        "coupon_valid": coupon_valid,
        "coupon_message": coupon_message,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
        "currency": "INR",
        "in_stock": bool(product["is_active"] and product["stock_quantity"] >= quantity),
        "available_stock": product["stock_quantity"]
    }
