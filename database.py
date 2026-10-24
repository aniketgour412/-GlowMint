import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional, Dict, Any, List

from config import DB_PATH, ADMIN_EMAIL, ADMIN_INITIAL_PASSWORD, STORE_NAME, SUPPORT_EMAIL, SUPPORT_PHONE
from auth import hash_password

logger = logging.getLogger("glowmint.database")

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Initialize database tables, default configurations, and seed admin user."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Product Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT,
                description TEXT NOT NULL,
                regular_price REAL NOT NULL,
                reference_price REAL NOT NULL,
                stock_quantity INTEGER NOT NULL DEFAULT 100,
                is_active INTEGER NOT NULL DEFAULT 1,
                images TEXT NOT NULL,
                features TEXT NOT NULL,
                care_instructions TEXT NOT NULL,
                package_contents TEXT NOT NULL,
                led_note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Coupons Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_percent REAL NOT NULL,
                max_discount REAL NOT NULL,
                min_order_val REAL NOT NULL DEFAULT 0.0,
                required_order_number INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                usage_count INTEGER NOT NULL DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Orders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                address_line TEXT NOT NULL,
                landmark TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                pincode TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                subtotal REAL NOT NULL,
                discount_amount REAL NOT NULL DEFAULT 0.0,
                coupon_code TEXT,
                shipping_fee REAL NOT NULL DEFAULT 0.0,
                total_amount REAL NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'razorpay',
                payment_status TEXT NOT NULL DEFAULT 'pending',
                order_status TEXT NOT NULL DEFAULT 'pending',
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_signature TEXT,
                tracking_number TEXT,
                courier_name TEXT,
                notes TEXT,
                idempotency_key TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indices for order queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(customer_phone);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(customer_email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status, order_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);")

        # 4. Admin Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Seed initial product if empty
        cursor.execute("SELECT COUNT(*) FROM products;")
        if cursor.fetchone()[0] == 0:
            default_images = json.dumps([
                "/static/images/hero.jpg",
                "/static/images/detail.jpg",
                "/static/images/packaging.jpg",
                "/static/images/model.jpg"
            ])
            default_features = json.dumps([
                "Traditional Moroccan-Indian filigree lantern dome motif with intricate openwork lattice",
                "Built-in warm ambient micro-LED inside each jhumka bell for luminous evening radiance",
                "Discreet, featherlight micro-toggle switch located beneath the inner lantern base",
                "Operates on replaceable LR41 coin cells (24+ hours continuous battery life)",
                "Crafted from hypoallergenic premium brass alloy with anti-tarnish champagne gold lacquer",
                "Artisan dangling seed pearl tassels and delicate ruby-tinted bead accents",
                "Ergonomically balanced weight (28g total pair) with secure push-back post closure"
            ])
            default_care = "Keep away from direct water, harsh perfumes, and hair sprays. Store in the complimentary airtight velvet pouch when not in use. Wipe gently with a dry microfiber cloth after wearing. Replace micro-cells via the twist-open base cap."
            default_package = "1x Pair GlowMint LED Lantern Jhumka Earrings, 1x Royal Plum Velvet Display Box, 1x Gold-Embossed Travel Pouch, 2x Extra LR41 Batteries, 1x Care & Authenticity Certificate."
            default_led_note = "Authentic Warm Ambient Glow: Each earring features a miniature, energy-efficient micro-LED core nestled inside the filigree dome. It produces an elegant golden aura without generating heat. Batteries are pre-installed, easily replaceable, and an extra fresh pair is included in every package."

            cursor.execute("""
                INSERT INTO products (
                    title, subtitle, description, regular_price, reference_price,
                    stock_quantity, is_active, images, features,
                    care_instructions, package_contents, led_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "LED Lantern Jhumka Earrings",
                "Traditional Indian Festive Heritage Meets Modern Luminous Craftsmanship",
                "Experience royal festive elegance with GlowMint's iconic LED Lantern Jhumkas. Hand-finished with intricate floral filigree metalwork and suspended seed pearls, each earring encloses a discreet, warm golden micro-LED that gently illuminates evening festivities, weddings, and celebrations with an unmistakable ethereal glow.",
                600.0,
                600.0,
                150,
                1,
                default_images,
                default_features,
                default_care,
                default_package,
                default_led_note
            ))

        # Seed initial coupons if empty
        cursor.execute("SELECT COUNT(*) FROM coupons;")
        if cursor.fetchone()[0] == 0:
            coupons_data = [
                ("FIRST50", 50.0, 500.0, 300.0, 1, 1, "50% OFF on your very first order at GlowMint Accessories (Max discount ₹500)"),
                ("SECOND20", 20.0, 300.0, 300.0, 2, 1, "20% OFF on your second order at GlowMint Accessories (Max discount ₹300)"),
                ("THIRD10", 10.0, 200.0, 300.0, 3, 1, "10% OFF on your third order at GlowMint Accessories (Max discount ₹200)")
            ]
            cursor.executemany("""
                INSERT INTO coupons (code, discount_percent, max_discount, min_order_val, required_order_number, is_active, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, coupons_data)

        # Seed initial admin user if empty
        cursor.execute("SELECT COUNT(*) FROM admin_users;")
        if cursor.fetchone()[0] == 0:
            pwd_hash, salt = hash_password(ADMIN_INITIAL_PASSWORD)
            cursor.execute("""
                INSERT INTO admin_users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            """, ("admin", ADMIN_EMAIL, pwd_hash, salt, "admin"))

        # Seed initial settings if empty
        default_settings = [
            ("announcement_bar", "Grand Launch Offer: Use code FIRST50 for 50% OFF your first order! • Free Insured Delivery Across India", "Top bar announcement text"),
            ("shipping_fee", "0.0", "Flat shipping fee in INR (0 for Free shipping)"),
            ("free_shipping_threshold", "0.0", "Minimum cart value for free shipping"),
            ("support_email", SUPPORT_EMAIL, "Customer support email"),
            ("support_phone", SUPPORT_PHONE, "Customer support phone/WhatsApp number"),
            ("support_hours", "Mon – Sat: 10:00 AM – 6:00 PM IST", "Customer support operational hours"),
            ("cod_status", "unavailable", "Cash on Delivery availability status"),
            ("cod_message", "Currently unavailable — prepaid orders only.", "Notice displayed to customer for Cash on Delivery"),
            ("razorpay_mode", "test", "Razorpay integration mode: test or live"),
            ("max_items_per_order", "5", "Maximum order quantity allowed per transaction")
        ]
        for key, val, desc in default_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            """, (key, val, desc))

def get_product() -> Optional[Dict[str, Any]]:
    """Retrieve the primary product record."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY id ASC LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        data["images"] = json.loads(data["images"])
        data["features"] = json.loads(data["features"])
        return data

def get_settings() -> Dict[str, str]:
    """Retrieve all store settings as a dictionary."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings;")
        rows = cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}

def get_customer_completed_orders_count(phone: str, email: str) -> int:
    """
    Count completed/paid orders associated with the customer's phone or email.
    Used for order history checks (FIRST50, SECOND20, THIRD10).
    """
    clean_phone = phone.strip()[-10:] if phone else ""
    clean_email = email.strip().lower() if email else ""

    with get_db() as conn:
        cursor = conn.cursor()
        # Count orders that are paid or verified
        cursor.execute("""
            SELECT COUNT(DISTINCT id) FROM orders
            WHERE (
                substr(customer_phone, -10) = ?
                OR lower(customer_email) = ?
            )
            AND payment_status IN ('paid', 'completed')
        """, (clean_phone, clean_email))
        count = cursor.fetchone()[0]
        return int(count)
