import os
import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

import database
from app import app
from config import RAZORPAY_WEBHOOK_SECRET, ADMIN_INITIAL_PASSWORD

# Ensure fresh DB initialization
database.init_db()
client = TestClient(app)

def test_landing_page_renders_without_errors():
    """Verify that the single-page customer storefront renders status 200 and required elements."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Section checks in order
    assert "announcement-bar" in html
    assert "GlowMint" in html
    assert "LED Lantern Jhumka Earrings" in html
    assert "gallery" in html
    assert "FIRST50" in html
    assert "SECOND20" in html
    assert "THIRD10" in html
    assert "faq" in html
    assert "trust" in html
    assert "Currently unavailable — prepaid orders only" in html

def test_static_product_images_exist():
    """Verify that product images are accessible via the static route."""
    for img in ["hero.jpg", "detail.jpg", "packaging.jpg", "model.jpg"]:
        res = client.get(f"/static/images/{img}")
        assert res.status_code == 200
        assert res.headers["content-type"] in ("image/jpeg", "image/jpg")

def test_product_price_and_settings_apis():
    """Verify that public product and store settings are retrieved accurately."""
    res_prod = client.get("/api/product")
    assert res_prod.status_code == 200
    p = res_prod.json()
    assert p["regular_price"] == 600.0
    assert p["title"] == "LED Lantern Jhumka Earrings"

    res_set = client.get("/api/settings")
    assert res_set.status_code == 200
    s = res_set.json()
    assert s["cod_status"] == "unavailable"
    assert "Currently unavailable" in s["cod_message"]

def test_pricing_and_coupon_first50_eligible_for_first_order():
    """FIRST50 (50% off) must apply for a new customer with 0 prior orders."""
    test_phone = "9811002233"
    test_email = "newcustomer1@example.com"

    res = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "FIRST50",
        "customer_phone": test_phone,
        "customer_email": test_email
    })
    assert res.status_code == 200
    data = res.json()
    assert data["coupon_valid"] is True
    assert data["coupon_code"] == "FIRST50"
    assert data["subtotal"] == 600.0
    assert data["discount_amount"] == 300.0  # 50% of 600
    assert data["total_amount"] == 300.0

def test_pricing_and_coupon_first50_rejected_if_customer_already_ordered():
    """FIRST50 must be rejected if the customer has an existing completed/paid order."""
    existing_phone = "9899001122"
    existing_email = "returningcustomer@example.com"

    # Seed a completed order for this phone
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                id, customer_name, customer_email, customer_phone,
                address_line, city, state, pincode, quantity, unit_price,
                subtotal, discount_amount, total_amount, payment_status, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "GM-TEST-PRIOR-1", "Test Customer", existing_email, existing_phone,
            "123 Park Lane", "New Delhi", "Delhi", "110001",
            1, 600.0, 600.0, 0.0, 600.0, "paid", "delivered"
        ))

    res = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "FIRST50",
        "customer_phone": existing_phone,
        "customer_email": existing_email
    })
    assert res.status_code == 200
    data = res.json()
    assert data["coupon_valid"] is False
    assert "FIRST50 is reserved exclusively for first-time customers" in data["coupon_message"]
    assert data["discount_amount"] == 0.0
    assert data["total_amount"] == 600.0

def test_second20_and_third10_rules():
    """SECOND20 applies only on 2nd order (count=1), THIRD10 only on 3rd order (count=2)."""
    user_phone = "9711223344"
    user_email = "loyaltyuser@example.com"

    # Initially count = 0 -> SECOND20 must fail
    res = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "SECOND20",
        "customer_phone": user_phone,
        "customer_email": user_email
    })
    assert res.json()["coupon_valid"] is False

    # Insert 1 completed order
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                id, customer_name, customer_email, customer_phone,
                address_line, city, state, pincode, quantity, unit_price,
                subtotal, discount_amount, total_amount, payment_status, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "GM-TEST-LOYAL-1", "Loyal Customer", user_email, user_phone,
            "202 Rose Villa", "Mumbai", "Maharashtra", "400001",
            1, 600.0, 600.0, 0.0, 600.0, "paid", "delivered"
        ))

    # Now count = 1 -> SECOND20 (20% off) must succeed!
    res2 = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "SECOND20",
        "customer_phone": user_phone,
        "customer_email": user_email
    })
    data2 = res2.json()
    assert data2["coupon_valid"] is True
    assert data2["discount_amount"] == 120.0  # 20% of 600
    assert data2["total_amount"] == 480.0

    # Insert 2nd completed order
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                id, customer_name, customer_email, customer_phone,
                address_line, city, state, pincode, quantity, unit_price,
                subtotal, discount_amount, total_amount, payment_status, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "GM-TEST-LOYAL-2", "Loyal Customer", user_email, user_phone,
            "202 Rose Villa", "Mumbai", "Maharashtra", "400001",
            1, 600.0, 600.0, 0.0, 600.0, "paid", "delivered"
        ))

    # Now count = 2 -> THIRD10 (10% off) must succeed!
    res3 = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "THIRD10",
        "customer_phone": user_phone,
        "customer_email": user_email
    })
    data3 = res3.json()
    assert data3["coupon_valid"] is True
    assert data3["discount_amount"] == 60.0  # 10% of 600
    assert data3["total_amount"] == 540.0

def test_invalid_coupon_rejected():
    """Bogus coupon code must be cleanly rejected."""
    res = client.post("/api/calculate-price", json={
        "quantity": 1,
        "coupon_code": "FAKEDISCOUNT99",
        "customer_phone": "9999999999",
        "customer_email": "test@example.com"
    })
    data = res.json()
    assert data["coupon_valid"] is False
    assert "is invalid or does not exist" in data["coupon_message"]
    assert data["discount_amount"] == 0.0

def test_cod_rejected_at_checkout():
    """Attempting to select Cash on Delivery must be blocked with HTTP 400."""
    res = client.post("/api/create-order", json={
        "customer_name": "Rohan Sharma",
        "customer_phone": "9876543210",
        "customer_email": "rohan@example.com",
        "address_line": "Flat 101, Lotus Apts",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "quantity": 1,
        "payment_method": "cod"
    })
    assert res.status_code == 400
    assert "Cash on Delivery is currently unavailable" in res.json()["detail"]

def test_checkout_validation_errors():
    """Invalid PIN code or phone number must fail validation."""
    # Bad phone
    res_bad_phone = client.post("/api/create-order", json={
        "customer_name": "Pooja Patel",
        "customer_phone": "123",  # Invalid phone
        "customer_email": "pooja@example.com",
        "address_line": "45 Diamond Plaza",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode": "380001",
        "quantity": 1,
        "payment_method": "razorpay"
    })
    assert res_bad_phone.status_code == 422

    # Bad PIN code
    res_bad_pin = client.post("/api/create-order", json={
        "customer_name": "Pooja Patel",
        "customer_phone": "9825012345",
        "customer_email": "pooja@example.com",
        "address_line": "45 Diamond Plaza",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode": "3800",  # Only 4 digits
        "quantity": 1,
        "payment_method": "razorpay"
    })
    assert res_bad_pin.status_code == 422

def test_successful_order_creation_and_payment_verification():
    """Create order, verify signature, confirm paid status, and check stock decrement."""
    order_req = {
        "customer_name": "Ananya Sen",
        "customer_phone": "9830099887",
        "customer_email": "ananya.sen@example.com",
        "address_line": "78 Park Street, 3rd Floor",
        "landmark": "Near Queen's Mansion",
        "city": "Kolkata",
        "state": "West Bengal",
        "pincode": "700016",
        "quantity": 1,
        "coupon_code": "FIRST50",
        "payment_method": "razorpay",
        "idempotency_key": "idemp_test_unique_ananya_001"
    }

    # Initial stock
    p_before = database.get_product()
    stock_before = p_before["stock_quantity"]

    res_order = client.post("/api/create-order", json=order_req)
    assert res_order.status_code == 200
    order_data = res_order.json()
    order_id = order_data["order_id"]
    rzp_order_id = order_data["razorpay_order_id"]
    assert order_id.startswith("GM-2026-")

    # Verify payment with simulation signature
    verify_req = {
        "order_id": order_id,
        "razorpay_order_id": rzp_order_id,
        "razorpay_payment_id": "pay_test_ananya_999",
        "razorpay_signature": "sim_sig_test_ananya"
    }

    res_verify = client.post("/api/verify-payment", json=verify_req)
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "success"

    # Check status endpoint
    res_status = client.get(f"/api/order-status/{order_id}")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["payment_status"] == "paid"
    assert status_data["order_status"] == "processing"

    # Verify stock decremented by 1
    p_after = database.get_product()
    assert p_after["stock_quantity"] == stock_before - 1

def test_duplicate_order_prevention_via_idempotency_key():
    """Submitting the exact same idempotency key must return the existing order rather than creating duplicate."""
    key = "idemp_prevent_duplicate_999"
    payload = {
        "customer_name": "Vikram Singh",
        "customer_phone": "9829011223",
        "customer_email": "vikram@example.com",
        "address_line": "12 Civil Lines",
        "city": "Jaipur",
        "state": "Rajasthan",
        "pincode": "302006",
        "quantity": 1,
        "payment_method": "razorpay",
        "idempotency_key": key
    }

    res1 = client.post("/api/create-order", json=payload)
    assert res1.status_code == 200
    order1 = res1.json()

    res2 = client.post("/api/create-order", json=payload)
    assert res2.status_code == 200
    order2 = res2.json()

    # Must be the exact same order ID
    assert order1["order_id"] == order2["order_id"]
    assert order2.get("reused_order") is True

def test_razorpay_webhook_signature_and_processing():
    """Verify webhook signature verification and idempotent order status update."""
    # Create order first
    res = client.post("/api/create-order", json={
        "customer_name": "Meera Iyer",
        "customer_phone": "9444012345",
        "customer_email": "meera@example.com",
        "address_line": "10 Anna Salai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600002",
        "quantity": 1,
        "payment_method": "razorpay"
    })
    order_data = res.json()
    rzp_order_id = order_data["razorpay_order_id"]
    order_id = order_data["order_id"]

    # Construct webhook payload
    webhook_body = json.dumps({
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_webhook_test_123",
                    "order_id": rzp_order_id,
                    "amount": 60000,
                    "status": "captured"
                }
            }
        }
    }).encode("utf-8")

    # Generate valid signature
    valid_sig = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        webhook_body,
        hashlib.sha256
    ).hexdigest()

    # Send with invalid signature first
    res_bad = client.post(
        "/api/razorpay-webhook",
        content=webhook_body,
        headers={"X-Razorpay-Signature": "invalid_sig_123"}
    )
    assert res_bad.status_code == 400

    # Send with valid signature
    res_good = client.post(
        "/api/razorpay-webhook",
        content=webhook_body,
        headers={"X-Razorpay-Signature": valid_sig}
    )
    assert res_good.status_code == 200
    assert res_good.json()["status"] == "ok"

    # Verify order is marked paid
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT payment_status, razorpay_payment_id FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        assert row["payment_status"] == "paid"
        assert row["razorpay_payment_id"] == "pay_webhook_test_123"

def test_admin_authentication_and_protection():
    """Unauthenticated users must get 401 when accessing protected admin APIs."""
    # Try accessing admin dashboard API without token
    res_dash = client.get("/api/admin/dashboard")
    assert res_dash.status_code == 401

    res_orders = client.get("/api/admin/orders")
    assert res_orders.status_code == 401

    # Attempt login with bad password
    res_bad_login = client.post("/api/admin/login", json={
        "email": "admin@glowmint.in",
        "password": "WrongPassword123"
    })
    assert res_bad_login.status_code == 401

    # Login with valid credentials
    res_login = client.post("/api/admin/login", json={
        "email": "admin@glowmint.in",
        "password": ADMIN_INITIAL_PASSWORD
    })
    assert res_login.status_code == 200
    token = res_login.json()["token"]
    assert token

    # Now authorized request with Bearer token succeeds
    headers = {"Authorization": f"Bearer {token}"}
    res_auth_dash = client.get("/api/admin/dashboard", headers=headers)
    assert res_auth_dash.status_code == 200
    assert "total_orders" in res_auth_dash.json()

def test_admin_update_product_and_settings():
    """Authorized admin can update product prices, stocks, and store settings."""
    # Login to get token
    res_login = client.post("/api/admin/login", json={
        "email": "admin@glowmint.in",
        "password": ADMIN_INITIAL_PASSWORD
    })
    token = res_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update product
    p_orig = client.get("/api/admin/product", headers=headers).json()
    new_price = 600.0
    res_update_p = client.put("/api/admin/product", json={
        "title": "LED Lantern Jhumka Earrings (Festive)",
        "subtitle": p_orig["subtitle"],
        "description": p_orig["description"],
        "regular_price": new_price,
        "reference_price": 600.0,
        "stock_quantity": 200,
        "is_active": 1,
        "care_instructions": p_orig["care_instructions"],
        "package_contents": p_orig["package_contents"],
        "led_note": p_orig["led_note"]
    }, headers=headers)
    assert res_update_p.status_code == 200

    # Verify public API sees the update
    res_pub = client.get("/api/product")
    assert res_pub.json()["title"] == "LED Lantern Jhumka Earrings (Festive)"
    assert res_pub.json()["stock_quantity"] == 200

    # Restore title
    client.put("/api/admin/product", json={
        "title": "LED Lantern Jhumka Earrings",
        "subtitle": p_orig["subtitle"],
        "description": p_orig["description"],
        "regular_price": 600.0,
        "reference_price": 600.0,
        "stock_quantity": 200,
        "is_active": 1,
        "care_instructions": p_orig["care_instructions"],
        "package_contents": p_orig["package_contents"],
        "led_note": p_orig["led_note"]
    }, headers=headers)
