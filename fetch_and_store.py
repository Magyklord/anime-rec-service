import requests
import sqlite3
import json

URL = "https://graphql.anilist.co"

# Notice we're now using GraphQL variables — exactly what you proposed
QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id #
    title {
      english
      romaji
    }
    genres
    description
  }
}
"""

def fetch_anime(anime_id):
    variables = {"id": anime_id}
    response = requests.post(URL, json={"query": QUERY, "variables": variables})
    return response.json()

def store_anime(data):
    media = data["data"]["Media"]

    # Use english title, fall back to romaji if english is None
    title = media["title"]["english"] or media["title"]["romaji"]
    description = media["description"]

    # Serialize the genres list to a JSON string for storage
    genres = json.dumps(media["genres"])

    conn = sqlite3.connect("anime.db")
    cursor = conn.cursor()

    # INSERT OR IGNORE means if this id already exists, skip it
    cursor.execute("""
        INSERT OR IGNORE INTO titles (id, title, description, genres)
        VALUES (?, ?, ?, ?)
    """, (media["id"] if "id" in media else None, title, description, genres))
    # Wait — spot the bug here. Where does the id come from in our query? -- id # is added in the graphQL query

    conn.commit()
    conn.close()

# Fetch and store a few titles
for anime_id in [1, 30, 20, 16498]:
    data = fetch_anime(anime_id)
    store_anime(data)
    print(f"Stored anime ID {anime_id}")