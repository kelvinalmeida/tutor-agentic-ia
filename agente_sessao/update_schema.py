
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Fallback config similar to docker-compose if env var is missing
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@control:5432/control_db")

# Try to connect and modify schema
try:
    print(f"Connecting to {DB_URL}...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='session' AND column_name='end_on_next_completion';
    """)
    if not cursor.fetchone():
        print("Adding column 'end_on_next_completion'...")
        cursor.execute("ALTER TABLE session ADD COLUMN end_on_next_completion BOOLEAN DEFAULT FALSE;")
        print("Column added.")
    else:
        print("Column 'end_on_next_completion' already exists.")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
