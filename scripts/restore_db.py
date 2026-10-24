#!/usr/bin/env python3
"""
GlowMint Accessories — SQLite Database Restore Script
Restores database from a designated backup file.
Usage: python3 scripts/restore_db.py <path_to_backup_file>
"""

import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DB_PATH

def run_restore(backup_file: Path):
    if not backup_file.exists():
        print(f"Error: Backup file {backup_file} does not exist.")
        sys.exit(1)

    print(f"Restoring database from {backup_file}...")

    # Create safety snapshot of current DB if exists
    if DB_PATH.exists():
        safety_path = DB_PATH.with_suffix(f".pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bak")
        print(f"Creating safety pre-restore backup at {safety_path}...")
        shutil.copy2(DB_PATH, safety_path)

    src = sqlite3.connect(str(backup_file))
    dst = sqlite3.connect(str(DB_PATH))

    with dst:
        src.backup(dst, pages=100)

    src.close()
    dst.close()

    print(f"Database successfully restored to {DB_PATH}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/restore_db.py <backup_file.sqlite3>")
        sys.exit(1)

    run_restore(Path(sys.argv[1]))
