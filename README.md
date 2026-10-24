# GlowMint Accessories — LED Lantern Jhumka Storefront & Merchant Suite

A high-performance, single-product e-commerce platform for **GlowMint Accessories**, selling traditional Indian LED lantern-style jhumka earrings.

---

## Project Status

**Current Classification**: **`C. Production Configuration Ready`**
- [x] Complete mobile-first customer storefront with verified sections and 3D visual assets.
- [x] Authoritative server-side pricing engine with milestone order history rules (`FIRST50`, `SECOND20`, `THIRD10`).
- [x] Streamlined checkout drawer with Indian mobile & PIN code validation and COD rejection.
- [x] Razorpay prepaid payment integration with HMAC-SHA256 signature verification and idempotent webhook handling.
- [x] Secure staff admin portal (`/admin`) with PBKDF2 password hashing, session cookies, KPI dashboard, order tracking, and CSV exports.
- [x] SQLite database with constraints, indexing, non-blocking online backup & restore scripts.
- [x] 20 automated tests passing with 100% success rate.
- [ ] *Pending final deployment*: Inserting merchant's live Razorpay production API keys in `.env` and pointing DNS to production host.

---

## Architecture & Technology Stack

- **Backend Framework**: Python 3 / FastAPI (Asynchronous, type-safe via Pydantic v2)
- **Security Middleware**: HTTP security headers (`nosniff`, `SAMEORIGIN`, `1; mode=block`, `strict-origin-when-cross-origin`, HSTS) and sliding-window rate limiting on login & checkout
- **Database**: SQLite3 (`glowmint.db`) with automatic schema initialization, constraints, and indexes
- **Frontend**: Responsive single-page application with Tailwind CSS, Google Fonts (*Playfair Display* & *Plus Jakarta Sans*), and vanilla ES6+ reactive state
- **Payment Gateway**: Official Razorpay integration supporting UPI, Debit/Credit Cards, and NetBanking with HMAC-SHA256 signature verification and idempotent webhook handling
- **Admin Portal**: Password-protected dashboard (`/admin`) utilizing PBKDF2-HMAC-SHA256 hashing and HTTP-only signed session tokens
- **Test Suite**: Automated Pytest test suite (`tests/test_storefront.py`) covering 20 comprehensive test cases

---

## Quickstart & Local Development

### 1. Run the Application
Start the development server using Uvicorn:

```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- Customer Storefront: `http://localhost:8000/`
- Admin Login: `http://localhost:8000/admin/login`
- Health Check: `http://localhost:8000/api/health`
- Swagger API Docs: `http://localhost:8000/docs`

### 2. Admin User Management
To provision or reset an administrator account via CLI without hardcoding passwords in files:

```bash
python3 scripts/create_admin.py --email admin@glowmint.in --password "YourStrongPassword!123"
```

---

## Production Deployment Guide

### 1. Environment Configuration (`.env`)
Create a production `.env` file from `.env.example`:

```env
PORT=8000
HOST=127.0.0.1
DEBUG=False
APP_SECRET_KEY=generate_a_random_64_character_hex_key_here

# Admin Credentials (used only on first startup if no admin exists)
ADMIN_EMAIL=admin@glowmint.in
ADMIN_INITIAL_PASSWORD=YourSecureProductionPassword!
ADMIN_SESSION_EXPIRE_HOURS=24

# Live Razorpay Credentials
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx

# Store Coordinates
STORE_NAME=GlowMint Accessories
STORE_CURRENCY=INR
SUPPORT_EMAIL=support@glowmint.in
SUPPORT_PHONE=+91 98765 43210
```

### 2. Systemd Service Setup (`/etc/systemd/system/glowmint.service`)
```ini
[Unit]
Description=GlowMint Accessories E-commerce Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/glowmint
EnvironmentFile=/var/www/glowmint/.env
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable glowmint
sudo systemctl start glowmint
```

### 3. Nginx Reverse Proxy Configuration (`/etc/nginx/sites-available/glowmint`)
```nginx
server {
    server_name glowmint.in www.glowmint.in;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/glowmint/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    client_max_body_size 10M;
}
```

Enable HTTPS using Let's Encrypt Certbot:
```bash
sudo certbot --nginx -d glowmint.in -d www.glowmint.in
```

---

## Database Backup & Restore Procedure

### Online Backup (Non-blocking)
To create a clean point-in-time snapshot using SQLite's native online backup API:

```bash
python3 scripts/backup_db.py
```
This writes a timestamped snapshot to `backups/glowmint_backup_YYYYMMDD_HHMMSS.sqlite3` without locking reads or writes.

### Safe Restore
To restore from a backup:

```bash
python3 scripts/restore_db.py backups/glowmint_backup_20261024_120000.sqlite3
```
*Note: A safety snapshot of the existing database is automatically created prior to restoring.*

---

## Automated Testing Suite

Run the full automated test suite:

```bash
python3 -m pytest -v tests/test_storefront.py
```

### Coverage (20 / 20 Tests Passing):
1. **Storefront Rendering**: Validates HTML output and ordered sections.
2. **Static Assets**: Verifies all 4 high-definition image views are accessible.
3. **Product & Store APIs**: Validates regular pricing and disabled COD policy.
4. **`FIRST50` Eligibility**: Validates 50% discount for first-time customers.
5. **`FIRST50` Rejection**: Verifies rejection when prior orders exist.
6. **`SECOND20` & `THIRD10` Rules**: Validates loyalty milestones based on order count.
7. **Invalid Coupon Rejection**: Ensures nonexistent or expired codes are rejected.
8. **COD Rejection**: Enforces HTTP 400 when attempting Cash on Delivery.
9. **Checkout Validation**: Validates 10-digit Indian phone numbers and 6-digit PIN codes.
10. **Order Lifecycle & Payment**: Verifies order persistence, HMAC signature check, and stock decrement.
11. **Idempotency**: Prevents duplicate order creation using idempotency keys.
12. **Webhook Signature Check**: Validates HMAC signature verification on webhooks.
13. **Admin Authentication**: Enforces HTTP 401 on protected endpoints and verifies valid JWT login.
14. **Admin Mutations**: Validates real-time product price and coupon updates.
15. **System Health Endpoint**: Validates `/api/health` status and DB connection.
16. **Payment Failure Reporting**: Verifies client failure recording in order records.
17. **Webhook `payment.failed`**: Verifies failed payment event handling.
18. **Webhook Idempotency**: Ensures duplicate deliveries do NOT double-decrement stock or double-count coupons.
19. **Backup & Restore**: Verifies non-blocking SQLite backup and restore integrity.
20. **Admin Rate Limiting**: Verifies HTTP 429 Too Many Requests upon rapid brute-force attempts.
