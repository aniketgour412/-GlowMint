# GlowMint Accessories — LED Lantern Jhumka Earrings Storefront

A production-oriented, mobile-first, single-product e-commerce platform for **GlowMint Accessories**, selling traditional Indian LED lantern-style jhumka earrings.

---

## Architecture & Technology Stack

- **Backend Framework**: Python 3 / FastAPI (Asynchronous, high-performance, type-safe via Pydantic v2)
- **Database**: SQLite3 (`glowmint.db`) with automatic schema migrations and indexing
- **Frontend**: Mobile-first single-page customer application with Tailwind CSS, Google Fonts (*Playfair Display* & *Plus Jakarta Sans*), and vanilla ES6+ reactive state
- **Payment Gateway**: Official Razorpay integration supporting UPI, Debit/Credit Cards, and NetBanking with HMAC-SHA256 signature verification and idempotent webhook handling
- **Admin Portal**: Secure password-protected dashboard (`/admin`) utilizing PBKDF2-HMAC-SHA256 hashing and HTTP-only signed session tokens
- **Test Suite**: Automated Pytest test suite (`tests/test_storefront.py`) with 100% pass coverage

---

## Key Features

### 1. Single-Page Customer Experience
- **Announcement Bar**: Displays active store promotion without false scarcity or countdown timers.
- **Brand Header**: Elegant GlowMint wordmark with cart summary indicator.
- **Hero Section**: High-resolution jewelry product showcase, clear regular pricing (₹600) and launch offer (₹300 with FIRST50), trust microcopy, and direct CTA.
- **Interactive Product Gallery**: 4 high-definition views (Hero presentation, Macro filigree detail, Packaging box, and Festive wear silhouette) plus an interactive LED illumination demonstration modal.
- **Milestone Coupons**:
  - `FIRST50`: 50% discount (up to ₹500 cap) for verified first-time orders.
  - `SECOND20`: 20% discount (up to ₹300 cap) for verified 2nd completed orders.
  - `THIRD10`: 10% discount (up to ₹200 cap) for verified 3rd completed orders.
  - *Server-side validation*: Coupons are validated against the customer's phone/email order history in SQLite. Coupon stacking is strictly prevented.
- **Product Details & LED Technology**: Verified specifications, 24+ hour runtime on replaceable coin cells, care instructions, and package contents.
- **Trust & Delivery Guarantees**: Insured courier dispatch (24–48 hours), 7-day transit replacement policy, and direct WhatsApp/Email customer care.
- **FAQ Accordion**: Honest answers regarding coupons, payment methods, delivery, and prepaid policies.
- **Footer & Legal Policies**: Modals for Privacy Policy, Terms & Conditions, Shipping Policy, and Return/Refund Policy.

### 2. Streamlined Checkout Drawer
- Responsive slide-over drawer accessible from any section.
- Quantity selector (1 to 5 units) with live price recalculation.
- Rigorous Indian delivery validation (10-digit mobile number, 6-digit postal PIN code, street address).
- **Cash on Delivery (COD)**: Explicitly disabled with badge *"Currently unavailable — prepaid orders only"*.
- **Prepaid Razorpay Checkout**:
  - In production: Launches official Razorpay popup with key ID and order ID.
  - In development / sandbox mode: Launches an integration-ready simulation modal that exercises the HMAC verification flow.

### 3. Merchant Control Panel (`/admin`)
- **Protected Access**: Route `/admin` requires staff authentication. Protected via `HttpOnly`, `SameSite=Lax` cookies.
- **Executive Dashboard**: Real-time KPI cards for verified paid revenue, total order count, average order value (AOV), and inventory level.
- **Orders Management**: Search by Customer Name / Phone / Order ID / Email, filter by fulfillment status (`paid`, `pending`, `processing`, `shipped`, `delivered`, `cancelled`). View delivery addresses, update courier partner & tracking numbers, add internal notes, and export orders to CSV.
- **Product & Inventory Editor**: Update regular price, reference price, stock quantity, active toggle, and product descriptions in real time.
- **Milestone Coupon Manager**: Configure discount percentages, caps, minimum order values, and order number requirements.
- **Store & Gateway Settings**: Edit announcement bar text, shipping fee rules, customer care phone/email, and inspect Razorpay integration status.

---

## Quickstart & Installation

### 1. Run the Application
The server runs directly using Python 3 and Uvicorn:

```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- Customer Storefront: `http://localhost:8000/`
- Admin Login: `http://localhost:8000/admin/login`
- Swagger API Docs: `http://localhost:8000/docs`

### 2. Default Seed Admin Credentials
- **Email**: `admin@glowmint.in`
- **Initial Password**: `GlowMint@Admin2026`

*(Credentials can be customized in `.env` before first initialization)*

---

## Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```env
PORT=8000
HOST=0.0.0.0
DEBUG=True
APP_SECRET_KEY=glowmint-secret-key-3b9e4a81f0c5421a8d9b2e7c4a152599c

# Admin Credentials
ADMIN_EMAIL=admin@glowmint.in
ADMIN_INITIAL_PASSWORD=GlowMint@Admin2026
ADMIN_SESSION_EXPIRE_HOURS=24

# Razorpay Configuration (Prepaid Payments)
RAZORPAY_KEY_ID=rzp_live_YourKeyHere
RAZORPAY_KEY_SECRET=YourSecretHere
RAZORPAY_WEBHOOK_SECRET=YourWebhookSecretHere

# Store Details
STORE_NAME=GlowMint Accessories
STORE_CURRENCY=INR
SUPPORT_EMAIL=support@glowmint.in
SUPPORT_PHONE=+91 98765 43210
```

---

## Running the Automated Test Suite

Run the full pytest suite:

```bash
python3 -m pytest -v tests/test_storefront.py
```

The 14 automated test cases verify:
1. Public customer landing page rendering and section order.
2. Static asset availability for all gallery perspectives.
3. Live pricing and store settings API output.
4. `FIRST50` qualification for first-time customers.
5. Rejection of `FIRST50` for customers with prior completed orders.
6. `SECOND20` and `THIRD10` milestone qualification based on completed order history.
7. Rejection of invalid, inactive, or substandard coupon codes.
8. Rejection of Cash on Delivery (COD) at checkout.
9. Form validation for customer phone numbers and Indian PIN codes.
10. Order creation, stock decrement, and HMAC payment signature verification.
11. Duplicate order prevention via idempotency keys.
12. Razorpay webhook signature verification and idempotent processing.
13. Prevention of unauthorized access to admin APIs (HTTP 401).
14. Authorized admin mutations for product pricing and store configuration.
