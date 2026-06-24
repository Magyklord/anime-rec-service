import sqlite3
import json

conn = sqlite3.connect("anime.db")
cursor = conn.cursor()

cursor.execute("SELECT id, title, genres FROM titles")
rows = cursor.fetchall()

for row in rows:
    anime_id, title, genres_json = row
    # Deserialize the JSON string back into a Python list because the original datatype exported from anilist cant be processed by sqlite
    genres = json.loads(genres_json)
    print(f"[{anime_id}] {title} — {genres}")

conn.close()