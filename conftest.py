import os
import sys
from pathlib import Path
import pytest

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

test_db_path = root_dir / "test_glowmint.db"
os.environ["GLOWMINT_DB_PATH"] = str(test_db_path)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure clean test database for test session."""
    if test_db_path.exists():
        test_db_path.unlink()
    
    import database
    import config
    config.DB_PATH = test_db_path
    database.DB_PATH = test_db_path
    database.init_db()

    yield

    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass
