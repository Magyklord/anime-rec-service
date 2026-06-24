"""
Restores the animedb PostgreSQL database from the included animedb_dump.zip.
Run this once after cloning instead of running paginator.py.

Usage:
    python restore_db.py
"""

import os
import subprocess
import zipfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DUMP_ZIP = Path(__file__).parent / "animedb_dump.zip"
DUMP_SQL = Path(__file__).parent / "animedb_dump.sql"

def main():
    if not DUMP_ZIP.exists():
        print("Error: animedb_dump.zip not found. Make sure you cloned the full repo.")
        return

    pg_password = os.environ.get("PG_PASSWORD")
    if not pg_password:
        print("Error: PG_PASSWORD not set in .env file.")
        return

    env = {**os.environ, "PGPASSWORD": pg_password}

    print("Extracting dump...")
    with zipfile.ZipFile(DUMP_ZIP, "r") as z:
        z.extractall(Path(__file__).parent)

    print("Creating database (if it doesn't exist)...")
    subprocess.run(
        ["psql", "-U", "postgres", "-c", "CREATE DATABASE animedb;"],
        env=env, capture_output=True
    )

    print("Restoring data (this may take a minute)...")
    result = subprocess.run(
        ["psql", "-U", "postgres", "-d", "animedb", "-f", str(DUMP_SQL)],
        env=env, capture_output=True, text=True
    )

    DUMP_SQL.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"Restore failed:\n{result.stderr}")
    else:
        print("Done. Database restored — you can now run app.py or cli.py.")

if __name__ == "__main__":
    main()
