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

    with database.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admin_users (username, email, password_hash, salt, role)
            VALUES (?, ?, ?, ?, 'admin')
            ON CONFLICT(email) DO UPDATE SET
                password_hash = excluded.password_hash,
                salt = excluded.salt;
        """, (username, email.strip().lower(), pwd_hash, salt))

    print(f"Admin user '{email}' provisioned / updated successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update an admin user for GlowMint Accessories.")
    parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Strong admin password")

    args = parser.parse_args()
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    provision_admin(args.username, args.email, args.password)
