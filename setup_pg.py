import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

def get_conn(dbname="animedb"):
    return psycopg2.connect(
        dbname=dbname,
        user="postgres",
        password=os.environ.get("PG_PASSWORD"),
        host="localhost",
        port="5432"
    )

# ── Step 1: Create the database if it doesn't exist ──────────────────────────
conn = get_conn(dbname="postgres")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'animedb'")
if not cursor.fetchone():
    cursor.execute("CREATE DATABASE animedb")
    print("Created database: animedb")
else:
    print("Database animedb already exists.")

conn.close()

# ── Step 2: Create or update tables ──────────────────────────────────────────
conn = get_conn()
cursor = conn.cursor()

# Main titles table — two new columns added: average_score and popularity.
# These come directly from AniList and power the hybrid scorer in Phase 3.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS titles (
        id            INTEGER PRIMARY KEY,
        title         TEXT,
        description   TEXT,
        genres        TEXT,
        tags          TEXT,
        average_score INTEGER,
        popularity    INTEGER
    )
""")

# Migration guard: if the table already existed without the new columns,
# ADD COLUMN IF NOT EXISTS silently skips rather than erroring.
cursor.execute("ALTER TABLE titles ADD COLUMN IF NOT EXISTS average_score INTEGER")
cursor.execute("ALTER TABLE titles ADD COLUMN IF NOT EXISTS popularity    INTEGER")

# Embeddings table: vector stored as a plain float array.
# 768 floats per row to match BAAI/bge-base-en-v1.5 output.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id      INTEGER PRIMARY KEY REFERENCES titles(id) ON DELETE CASCADE,
        vector  FLOAT[]
    )
""")

conn.commit()
conn.close()
print("Schema ready.")
