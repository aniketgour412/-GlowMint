#!/usr/bin/env python3
"""
GlowMint Accessories — Safe Online SQLite Database Backup Script
Utilizes SQLite's native non-blocking online backup API.
Usage: python3 scripts/backup_db.py [optional_backup_path]
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DB_PATH

def run_backup(target_path: Path = None):
    if not DB_PATH.exists():
        print(f"Error: Database {DB_PATH} does not exist.")
        sys.exit(1)

    if target_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        target_path = backup_dir / f"glowmint_backup_{timestamp}.sqlite3"

    print(f"Backing up {DB_PATH} to {target_path}...")

    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(target_path))

    with dst:
        src.backup(dst, pages=100)

    src.close()
    dst.close()

    print(f"Backup completed successfully: {target_path} ({target_path.stat().st_size} bytes)")
    return target_path

if __name__ == "__main__":
    custom_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    run_backup(custom_path)
