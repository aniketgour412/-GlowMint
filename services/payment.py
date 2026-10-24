import hmac
import hashlib
import json
import secrets
import logging
from typing import Dict, Any, Tuple, Optional
import requests
from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, DEBUG

logger = logging.getLogger("glowmint.payment")

def is_real_razorpay_configured() -> bool:
    """Check if valid non-placeholder Razorpay credentials are provided."""
    key = RAZORPAY_KEY_ID or ""
    secret = RAZORPAY_KEY_SECRET or ""
    return (
        bool(key and secret)
        and not key.startswith("rzp_test_Your")
        and not key.startswith("rzp_test_glowmintdemo")
        and len(key) > 10
        and len(secret) > 10
    )

def create_razorpay_order(order_id: str, amount_inr: float) -> Dict[str, Any]:
    """
    Create an order via Razorpay API.
    In production: strictly uses real Razorpay API or raises setup requirement.
    In debug/test: allows integration-ready simulation for QA.
    """
    amount_paise = int(round(amount_inr * 100))

    if is_real_razorpay_configured():
        try:
            url = "https://api.razorpay.com/v1/orders"
            payload = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": order_id,
                "notes": {
                    "order_id": order_id,
                    "store": "GlowMint Accessories",
                    "product": "LED Lantern Jhumka Earrings"
                }
            }
            resp = requests.post(
                url,
                json=payload,
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                timeout=10.0
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "razorpay_order_id": data["id"],
                    "amount": data["amount"],
                    "currency": data["currency"],
                    "key_id": RAZORPAY_KEY_ID,
                    "mode": "live"
                }
            else:
                logger.error(f"Razorpay API error {resp.status_code}: {resp.text}")
                if not DEBUG:
                    raise RuntimeError(f"Razorpay order creation failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Razorpay connection failed: {e}")
            if not DEBUG:
                raise RuntimeError(f"Unable to contact Razorpay gateway: {e}")

    # If in production and real credentials are not valid:
    if not DEBUG:
        raise ValueError(
            "Razorpay payment gateway is not configured for production. "
            "Please provide valid RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env."
        )

    # In Debug / Testing mode only: return clearly labelled simulation
    simulated_order_id = f"order_sim_{secrets.token_hex(8)}"
    return {
        "razorpay_order_id": simulated_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID or "rzp_test_simulation",
        "mode": "simulation",
        "note": "Test / Simulation Mode Active. Provide live RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET in .env for production gateway."
    }

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Verify payment signature using HMAC-SHA256 according to official Razorpay specifications.
    Simulated signatures are strictly rejected in production (when DEBUG=False).
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    secret = RAZORPAY_KEY_SECRET or ""
    if secret:
        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        if secrets.compare_digest(expected_sig, razorpay_signature):
            return True

    # In Debug/Testing mode only, accept simulation signatures
    if DEBUG and razorpay_order_id.startswith("order_sim_") and razorpay_signature.startswith("sim_sig_"):
        return True

    return False

def verify_webhook_signature(raw_body: bytes, received_signature: str) -> bool:
    """
    Verify Razorpay Webhook signature using HMAC-SHA256 with RAZORPAY_WEBHOOK_SECRET.
    """
    if not RAZORPAY_WEBHOOK_SECRET or not received_signature:
        return False

    computed = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return secrets.compare_digest(computed, received_signature)
