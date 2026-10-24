import os
import csv
import io
import re
import json
import time
import secrets
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query, status, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, EmailStr, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from config import (
    BASE_DIR, PORT, HOST, DEBUG, APP_SECRET_KEY,
    RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET,
    STORE_NAME, STORE_CURRENCY, SUPPORT_EMAIL, SUPPORT_PHONE,
    ADMIN_SESSION_EXPIRE_HOURS
)
import database
from auth import (
    hash_password, verify_password, create_admin_token, decode_admin_token
)
from services.pricing import calculate_order_pricing
from services.payment import (
    create_razorpay_order, verify_payment_signature, verify_webhook_signature, is_real_razorpay_configured
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("glowmint.app")

# Ensure database is initialized
database.init_db()

from fastapi.exceptions import RequestValidationError

app = FastAPI(
    title="GlowMint Accessories",
    description="Official storefront and management platform for GlowMint LED Lantern Jhumka Earrings",
    version="1.0.0"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = str(err.get("loc", ["field"])[-1])
        msg = err.get("msg", "Invalid value").replace("Value error, ", "")
        errors.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": ", ".join(errors)}
    )

# -----------------------------------------------------------------------------
# Security Headers Middleware
# -----------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Simple sliding-window rate limiter dictionary: ip -> list of timestamps
_rate_limits: Dict[str, List[float]] = {}

def reset_rate_limits():
    """Clear in-memory rate limit logs (useful for testing and maintenance)."""
    _rate_limits.clear()

def rate_limiter(max_calls: int = 60, window_seconds: int = 60):
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        calls = _rate_limits.setdefault(client_ip, [])
        # filter out calls older than window
        calls = [t for t in calls if now - t < window_seconds]
        if len(calls) >= max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment before trying again.")
        calls.append(now)
        _rate_limits[client_ip] = calls
        return True
    return dependency

# -----------------------------------------------------------------------------
# Admin Authentication Dependency
# -----------------------------------------------------------------------------
def get_current_admin(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("glowmint_admin_token")
    auth_header = request.headers.get("Authorization")
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access admin functions"
        )
    payload = decode_admin_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session"
        )
    return payload

# -----------------------------------------------------------------------------
# Pydantic Request / Response Schemas
# -----------------------------------------------------------------------------
class PriceCheckRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=10)
    coupon_code: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

class CreateOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=15)
    customer_email: str = Field(..., min_length=5, max_length=100)
    address_line: str = Field(..., min_length=5, max_length=255)
    landmark: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=10)
    quantity: int = Field(default=1, ge=1, le=10)
    coupon_code: Optional[str] = None
    payment_method: str = Field(default="razorpay")
    idempotency_key: Optional[str] = None

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^\d]", "", v)
        if len(clean) < 10:
            raise ValueError("Please provide a valid 10-digit mobile number.")
        return clean[-10:]

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        clean = re.sub(r"[^\d]", "", v)
        if len(clean) != 6:
            raise ValueError("Please provide a valid 6-digit Indian postal PIN code.")
        return clean

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v:
            raise ValueError("Please enter a valid email address.")
        return v

class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class RecordPaymentFailureRequest(BaseModel):
    order_id: str
    reason: Optional[str] = "Customer cancelled or closed checkout modal"

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class UpdateOrderStatusRequest(BaseModel):
    order_status: Optional[str] = None
    payment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None
    notes: Optional[str] = None

class ProductUpdateRequest(BaseModel):
    title: str
    subtitle: Optional[str] = ""
    description: str
    regular_price: float
    reference_price: float
    stock_quantity: int
    is_active: int
    care_instructions: Optional[str] = ""
    package_contents: Optional[str] = ""
    led_note: Optional[str] = ""

class CouponUpdateRequest(BaseModel):
    discount_percent: float
    max_discount: float
    min_order_val: float
    required_order_number: int
    is_active: int
    description: Optional[str] = ""

class CouponCreateRequest(BaseModel):
    code: str
    discount_percent: float
    max_discount: float
    min_order_val: float
    required_order_number: int = 0
    is_active: int = 1
    description: Optional[str] = ""

# -----------------------------------------------------------------------------
# Frontend Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    product = database.get_product()
    settings = database.get_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "product": product,
            "settings": settings,
            "store_name": STORE_NAME,
            "razorpay_key_id": RAZORPAY_KEY_ID,
            "is_razorpay_live": is_real_razorpay_configured(),
            "debug_mode": DEBUG
        }
    )

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    token = request.cookies.get("glowmint_admin_token")
    if token and decode_admin_token(token):
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"store_name": STORE_NAME}
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    token = request.cookies.get("glowmint_admin_token")
    if not token or not decode_admin_token(token):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"store_name": STORE_NAME}
    )

# -----------------------------------------------------------------------------
# Public API Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    """System health check and diagnostic status."""
    try:
        with database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "razorpay_configured": is_real_razorpay_configured(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/product")
async def get_product_api():
    product = database.get_product()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/api/settings")
async def get_settings_api():
    settings = database.get_settings()
    return {
        "announcement_bar": settings.get("announcement_bar", ""),
        "support_email": settings.get("support_email", SUPPORT_EMAIL),
        "support_phone": settings.get("support_phone", SUPPORT_PHONE),
        "support_hours": settings.get("support_hours", "Mon – Sat: 10:00 AM – 6:00 PM IST"),
        "cod_status": settings.get("cod_status", "unavailable"),
        "cod_message": settings.get("cod_message", "Currently unavailable — prepaid orders only."),
        "currency": STORE_CURRENCY
    }

@app.post("/api/calculate-price", dependencies=[Depends(rate_limiter(max_calls=40, window_seconds=60))])
async def calculate_price_api(req: PriceCheckRequest):
    try:
        pricing = calculate_order_pricing(
            quantity=req.quantity,
            coupon_code=req.coupon_code,
            customer_phone=req.customer_phone,
            customer_email=req.customer_email,
            check_concurrent_pending=False
        )
        return pricing
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        raise HTTPException(status_code=500, detail="Unable to calculate price at this moment.")

@app.post("/api/create-order", dependencies=[Depends(rate_limiter(max_calls=20, window_seconds=60))])
async def create_order_api(req: CreateOrderRequest):
    # Reject COD strictly as required
    if req.payment_method.lower() in ("cod", "cash_on_delivery", "cashondelivery"):
        raise HTTPException(
            status_code=400,
            detail="Cash on Delivery is currently unavailable — prepaid orders only."
        )

    if req.payment_method.lower() != "razorpay":
        raise HTTPException(status_code=400, detail="Invalid payment method. Only Razorpay prepaid checkout is supported.")

    # Prevent duplicate submission via idempotency key
    if req.idempotency_key:
        with database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE idempotency_key = ?", (req.idempotency_key,))
            existing = cursor.fetchone()
            if existing:
                order_data = dict(existing)
                return {
                    "order_id": order_data["id"],
                    "razorpay_order_id": order_data["razorpay_order_id"],
                    "amount": int(round(order_data["total_amount"] * 100)),
                    "currency": "INR",
                    "key_id": RAZORPAY_KEY_ID,
                    "reused_order": True
                }

    # Authoritative server-side price calculation with concurrency check
    try:
        pricing = calculate_order_pricing(
            quantity=req.quantity,
            coupon_code=req.coupon_code,
            customer_phone=req.customer_phone,
            customer_email=req.customer_email,
            check_concurrent_pending=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not pricing["in_stock"]:
        raise HTTPException(status_code=400, detail="The requested quantity is currently out of stock.")

    # Generate unique readable Order ID: GM-2026-XXXX
    order_num = secrets.randbelow(9000) + 1000
    unique_order_id = f"GM-2026-{order_num}"

    # Ensure uniqueness
    with database.get_db() as conn:
        cursor = conn.cursor()
        while True:
            cursor.execute("SELECT 1 FROM orders WHERE id = ?", (unique_order_id,))
            if not cursor.fetchone():
                break
            unique_order_id = f"GM-2026-{secrets.randbelow(9000) + 1000}"

    # Create Razorpay order
    try:
        rzp_info = create_razorpay_order(unique_order_id, pricing["total_amount"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment gateway order: {e}")
        raise HTTPException(status_code=500, detail="Unable to initiate payment transaction.")

    # Persist pending order
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (
                id, customer_name, customer_email, customer_phone,
                address_line, landmark, city, state, pincode,
                quantity, unit_price, subtotal, discount_amount, coupon_code,
                shipping_fee, total_amount, payment_method, payment_status,
                order_status, razorpay_order_id, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unique_order_id,
            req.customer_name.strip(),
            req.customer_email.strip().lower(),
            req.customer_phone.strip(),
            req.address_line.strip(),
            req.landmark.strip() if req.landmark else "",
            req.city.strip(),
            req.state.strip(),
            req.pincode.strip(),
            pricing["quantity"],
            pricing["unit_price"],
            pricing["subtotal"],
            pricing["discount_amount"],
            pricing["coupon_code"],
            pricing["shipping_fee"],
            pricing["total_amount"],
            "razorpay",
            "pending",
            "pending",
            rzp_info["razorpay_order_id"],
            req.idempotency_key
        ))

    return {
        "order_id": unique_order_id,
        "razorpay_order_id": rzp_info["razorpay_order_id"],
        "amount": rzp_info["amount"],
        "currency": rzp_info["currency"],
        "key_id": rzp_info["key_id"],
        "mode": rzp_info.get("mode", "simulation"),
        "customer": {
            "name": req.customer_name,
            "email": req.customer_email,
            "phone": req.customer_phone
        },
        "pricing": pricing
    }

@app.post("/api/verify-payment", dependencies=[Depends(rate_limiter(max_calls=30, window_seconds=60))])
async def verify_payment_api(req: VerifyPaymentRequest):
    # Verify signature
    is_valid = verify_payment_signature(
        req.razorpay_order_id,
        req.razorpay_payment_id,
        req.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed. Invalid payment signature."
        )

    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (req.order_id,))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Idempotent check
        if order["payment_status"] == "paid":
            return {
                "status": "success",
                "message": "Payment already confirmed.",
                "order_id": order["id"],
                "total_amount": order["total_amount"]
            }

        # Atomic transition to paid
        cursor.execute("""
            UPDATE orders
            SET payment_status = 'paid',
                order_status = 'processing',
                razorpay_payment_id = ?,
                razorpay_signature = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND payment_status != 'paid'
        """, (req.razorpay_payment_id, req.razorpay_signature, req.order_id))

        if cursor.rowcount == 1:
            # Decrement product stock safely
            cursor.execute("""
                UPDATE products
                SET stock_quantity = MAX(0, stock_quantity - ?)
                WHERE id = 1
            """, (order["quantity"],))

            # Increment coupon usage count if used
            if order["coupon_code"]:
                cursor.execute("""
                    UPDATE coupons
                    SET usage_count = usage_count + 1
                    WHERE UPPER(code) = UPPER(?)
                """, (order["coupon_code"],))

    return {
        "status": "success",
        "message": "Payment verified and order confirmed successfully!",
        "order_id": req.order_id,
        "payment_id": req.razorpay_payment_id
    }

@app.post("/api/record-payment-failure")
async def record_payment_failure_api(req: RecordPaymentFailureRequest):
    """Record customer payment dismissal or failure."""
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders
            SET payment_status = 'failed',
                notes = COALESCE(notes, '') || ' [Customer payment failed or cancelled: ' || ? || ']',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND payment_status = 'pending'
        """, (req.reason, req.order_id))
    return {"status": "recorded"}

@app.post("/api/razorpay-webhook")
async def razorpay_webhook_api(request: Request, x_razorpay_signature: Optional[str] = Header(None)):
    raw_body = await request.body()

    # Webhook signature verification
    if not verify_webhook_signature(raw_body, x_razorpay_signature or ""):
        logger.warning("Razorpay webhook signature verification failed.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body.decode("utf-8"))
        event_name = event.get("event")

        if event_name in ("payment.captured", "order.paid"):
            payload_payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payload_payment.get("order_id")
            razorpay_payment_id = payload_payment.get("id")

            if razorpay_order_id:
                with database.get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM orders WHERE razorpay_order_id = ?", (razorpay_order_id,))
                    order = cursor.fetchone()
                    if order and order["payment_status"] != "paid":
                        cursor.execute("""
                            UPDATE orders
                            SET payment_status = 'paid',
                                order_status = 'processing',
                                razorpay_payment_id = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ? AND payment_status != 'paid'
                        """, (razorpay_payment_id, order["id"]))

                        if cursor.rowcount == 1:
                            cursor.execute("""
                                UPDATE products
                                SET stock_quantity = MAX(0, stock_quantity - ?)
                                WHERE id = 1
                            """, (order["quantity"],))

                            if order["coupon_code"]:
                                cursor.execute("""
                                    UPDATE coupons
                                    SET usage_count = usage_count + 1
                                    WHERE UPPER(code) = UPPER(?)
                                """, (order["coupon_code"],))

        elif event_name == "payment.failed":
            payload_payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payload_payment.get("order_id")
            error_desc = payload_payment.get("error_description", "Payment failed")
            if razorpay_order_id:
                with database.get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE orders
                        SET payment_status = 'failed',
                            notes = COALESCE(notes, '') || ' [Razorpay webhook reported failure: ' || ? || ']',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE razorpay_order_id = ? AND payment_status = 'pending'
                    """, (error_desc, razorpay_order_id))

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/api/order-status/{order_id}")
async def get_order_status_api(order_id: str):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, quantity, total_amount, payment_status, order_status,
                   tracking_number, courier_name, created_at
            FROM orders
            WHERE id = ?
        """, (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(row)

# -----------------------------------------------------------------------------
# Admin Protected API Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/admin/login", dependencies=[Depends(rate_limiter(max_calls=5, window_seconds=60))])
async def admin_login_api(req: AdminLoginRequest, response: Response):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE lower(email) = lower(?)", (req.email.strip(),))
        user = cursor.fetchone()
        if not user or not verify_password(req.password, user["password_hash"], user["salt"]):
            raise HTTPException(status_code=401, detail="Invalid admin credentials")

        token = create_admin_token(user["id"], user["username"], user["email"])
        max_age_seconds = ADMIN_SESSION_EXPIRE_HOURS * 3600
        response.set_cookie(
            key="glowmint_admin_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=max_age_seconds,
            secure=not DEBUG
        )
        return {
            "status": "success",
            "message": "Login successful",
            "token": token,
            "user": {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        }

@app.post("/api/admin/logout")
async def admin_logout_api(response: Response):
    response.delete_cookie(key="glowmint_admin_token")
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/admin/dashboard")
async def admin_dashboard_api(admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0.0) FROM orders WHERE payment_status = 'paid';")
        paid_orders, paid_revenue = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM orders;")
        total_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'pending';")
        pending_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'shipped';")
        shipped_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'delivered';")
        delivered_orders = cursor.fetchone()[0]

        aov = round(paid_revenue / paid_orders, 2) if paid_orders > 0 else 0.0

        # Recent 5 orders
        cursor.execute("""
            SELECT id, customer_name, customer_phone, total_amount, payment_status, order_status, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT 5;
        """)
        recent_orders = [dict(r) for r in cursor.fetchall()]

        # Product stock
        product = database.get_product()

        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "paid_revenue": round(paid_revenue, 2),
            "pending_orders": pending_orders,
            "shipped_orders": shipped_orders,
            "delivered_orders": delivered_orders,
            "average_order_value": aov,
            "recent_orders": recent_orders,
            "product_stock": product["stock_quantity"] if product else 0,
            "is_in_stock": product["is_active"] if product else 0
        }

@app.get("/api/admin/orders")
async def admin_list_orders_api(
    admin: Dict[str, Any] = Depends(get_current_admin),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    offset = (page - 1) * limit
    where_clauses = []
    params = []

    if search:
        s = f"%{search.strip()}%"
        where_clauses.append("(id LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ? OR customer_email LIKE ?)")
        params.extend([s, s, s, s])

    if status_filter and status_filter.lower() != "all":
        where_clauses.append("(order_status = ? OR payment_status = ?)")
        params.extend([status_filter.lower(), status_filter.lower()])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM orders {where_sql};", params)
        total_count = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT id, customer_name, customer_email, customer_phone, city, state, pincode,
                   quantity, subtotal, discount_amount, coupon_code, total_amount,
                   payment_status, order_status, tracking_number, courier_name, created_at
            FROM orders
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """, params + [limit, offset])
        orders = [dict(r) for r in cursor.fetchall()]

        return {
            "orders": orders,
            "total": total_count,
            "page": page,
            "pages": (total_count + limit - 1) // limit if total_count > 0 else 1
        }

@app.get("/api/admin/orders/{order_id}")
async def admin_get_order_api(order_id: str, admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(order)

@app.patch("/api/admin/orders/{order_id}")
async def admin_update_order_api(order_id: str, req: UpdateOrderStatusRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Order not found")

        updates = []
        params = []
        if req.order_status is not None:
            updates.append("order_status = ?")
            params.append(req.order_status)
        if req.payment_status is not None:
            updates.append("payment_status = ?")
            params.append(req.payment_status)
        if req.tracking_number is not None:
            updates.append("tracking_number = ?")
            params.append(req.tracking_number)
        if req.courier_name is not None:
            updates.append("courier_name = ?")
            params.append(req.courier_name)
        if req.notes is not None:
            updates.append("notes = ?")
            params.append(req.notes)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            sql = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"
            params.append(order_id)
            cursor.execute(sql, params)

        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        updated = cursor.fetchone()
        return dict(updated)

@app.get("/api/admin/orders-export")
async def admin_export_orders_csv(admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_name, customer_email, customer_phone,
                   address_line, landmark, city, state, pincode,
                   quantity, unit_price, subtotal, discount_amount, coupon_code,
                   shipping_fee, total_amount, payment_status, order_status,
                   razorpay_payment_id, tracking_number, courier_name, created_at
            FROM orders
            ORDER BY created_at DESC;
        """)
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Order ID", "Customer Name", "Email", "Phone",
            "Address", "Landmark", "City", "State", "PIN Code",
            "Quantity", "Unit Price", "Subtotal", "Discount", "Coupon",
            "Shipping", "Total Amount", "Payment Status", "Order Status",
            "Razorpay Payment ID", "Tracking Number", "Courier", "Date"
        ])
        for r in rows:
            writer.writerow([
                r["id"], r["customer_name"], r["customer_email"], r["customer_phone"],
                r["address_line"], r["landmark"], r["city"], r["state"], r["pincode"],
                r["quantity"], r["unit_price"], r["subtotal"], r["discount_amount"], r["coupon_code"],
                r["shipping_fee"], r["total_amount"], r["payment_status"], r["order_status"],
                r["razorpay_payment_id"], r["tracking_number"], r["courier_name"], r["created_at"]
            ])

        output.seek(0)
        filename = f"glowmint_orders_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@app.get("/api/admin/product")
async def admin_get_product(admin: Dict[str, Any] = Depends(get_current_admin)):
    product = database.get_product()
    return product

@app.put("/api/admin/product")
async def admin_update_product(req: ProductUpdateRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products
            SET title = ?, subtitle = ?, description = ?,
                regular_price = ?, reference_price = ?,
                stock_quantity = ?, is_active = ?,
                care_instructions = ?, package_contents = ?, led_note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1;
        """, (
            req.title, req.subtitle, req.description,
            req.regular_price, req.reference_price,
            req.stock_quantity, req.is_active,
            req.care_instructions, req.package_contents, req.led_note
        ))
    return {"status": "success", "message": "Product updated successfully"}

@app.get("/api/admin/coupons")
async def admin_get_coupons(admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coupons ORDER BY id ASC;")
        coupons = [dict(r) for r in cursor.fetchall()]
        return coupons

@app.put("/api/admin/coupons/{coupon_id}")
async def admin_update_coupon(coupon_id: int, req: CouponUpdateRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE coupons
            SET discount_percent = ?, max_discount = ?, min_order_val = ?,
                required_order_number = ?, is_active = ?, description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (
            req.discount_percent, req.max_discount, req.min_order_val,
            req.required_order_number, req.is_active, req.description,
            coupon_id
        ))
    return {"status": "success", "message": "Coupon updated successfully"}

@app.post("/api/admin/coupons")
async def admin_create_coupon(req: CouponCreateRequest, admin: Dict[str, Any] = Depends(get_current_admin)):
    code = req.code.strip().upper()
    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM coupons WHERE UPPER(code) = ?", (code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Coupon code {code} already exists")

        cursor.execute("""
            INSERT INTO coupons (code, discount_percent, max_discount, min_order_val, required_order_number, is_active, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            code, req.discount_percent, req.max_discount, req.min_order_val,
            req.required_order_number, req.is_active, req.description
        ))
    return {"status": "success", "message": f"Coupon {code} created successfully"}

@app.get("/api/admin/settings")
async def admin_get_settings(admin: Dict[str, Any] = Depends(get_current_admin)):
    settings = database.get_settings()
    settings["razorpay_configured"] = "true" if is_real_razorpay_configured() else "false"
    settings["razorpay_key_preview"] = (RAZORPAY_KEY_ID[:8] + "...") if RAZORPAY_KEY_ID else "Not Set"
    return settings

@app.put("/api/admin/settings")
async def admin_update_settings(updates: Dict[str, str], admin: Dict[str, Any] = Depends(get_current_admin)):
    with database.get_db() as conn:
        cursor = conn.cursor()
        for key, value in updates.items():
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP;
            """, (key, str(value)))
    return {"status": "success", "message": "Settings updated successfully"}
