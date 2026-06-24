import sqlite3

# Creates the file anime.db if it doesn't exist
# If it does exist, just connects to it
conn = sqlite3.connect("anime.db")

# A cursor is your tool for executing SQL statements
cursor = conn.cursor()

# Create the table
# IF NOT EXISTS means running this twice won't cause an error
cursor.execute("""
    CREATE TABLE IF NOT EXISTS titles (
        id          INTEGER PRIMARY KEY,
        title       TEXT,
        description TEXT,
        genres      TEXT
    )
""")

# Commit saves your changes permanently
conn.commit()

# Always close when done
conn.close()

print("Database and table created successfully.")