#!/usr/bin/env python3
"""
GlowMint Accessories — CLI Tool for Provisioning & Resetting Admin Users
Usage: python3 scripts/create_admin.py --email admin@glowmint.in --password StrongPassword!123
"""

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import database
from auth import hash_password

def provision_admin(username: str, email: str, password: str):
    database.init_db()
    pwd_hash, salt = hash_password(password)
    clean_email = email.strip().lower()
    
    # If username is left as default "admin" but email is different, use the email's handle
    if not username or (username == "admin" and clean_email != "admin@glowmint.in"):
        username = clean_email.split("@")[0]

    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM admin_users WHERE email = ?", (clean_email,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE admin_users
                SET password_hash = ?, salt = ?
                WHERE id = ?
            """, (pwd_hash, salt, existing["id"]))
            print(f"Admin user '{clean_email}' (username: {existing['username']}) password updated successfully.")
        else:
            # Check if desired username is already taken by another account
            cursor.execute("SELECT id FROM admin_users WHERE username = ?", (username,))
            if cursor.fetchone():
                import secrets
                username = f"{clean_email.split('@')[0]}_{secrets.token_hex(2)}"
            
            cursor.execute("""
                INSERT INTO admin_users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, 'admin')
            """, (username, clean_email, pwd_hash, salt))
            print(f"Admin user '{clean_email}' (username: {username}) provisioned successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update an admin user for GlowMint Accessories.")
    parser.add_argument("--username", default="admin", help="Admin username (default: email handle)")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Strong admin password")

    args = parser.parse_args()
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    provision_admin(args.username, args.email, args.password)

