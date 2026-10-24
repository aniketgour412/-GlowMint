import os
import sys
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Read .env manually if exists without requiring external packages
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

# In production, require strong APP_SECRET_KEY
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY")
if not APP_SECRET_KEY:
    if DEBUG:
        APP_SECRET_KEY = "glowmint-dev-secret-key-do-not-use-in-production-2026"
    else:
        # In production mode without secret key, exit safely or warn loudly
        logging.critical("CRITICAL SECURITY ERROR: APP_SECRET_KEY is not set in production!")
        sys.exit(1)

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@glowmint.in")
ADMIN_INITIAL_PASSWORD = os.environ.get("ADMIN_INITIAL_PASSWORD")
ADMIN_SESSION_EXPIRE_HOURS = int(os.environ.get("ADMIN_SESSION_EXPIRE_HOURS", 24))

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

STORE_NAME = os.environ.get("STORE_NAME", "GlowMint Accessories")
STORE_CURRENCY = os.environ.get("STORE_CURRENCY", "INR")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@glowmint.in")
SUPPORT_PHONE = os.environ.get("SUPPORT_PHONE", "+91 98765 43210")

DB_PATH = Path(os.environ.get("GLOWMINT_DB_PATH", BASE_DIR / "glowmint.db"))
