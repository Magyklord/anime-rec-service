import requests
import psycopg2
import os
import json
import time
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tag_expander import build_rich_soup

load_dotenv()

# BGE-base-en-v1.5: trained specifically for retrieval tasks.
# 768 dimensions (2x MiniLM), much better at matching mood queries to
# structured document text even when they share no words in common.
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

URL = "https://graphql.anilist.co"

QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { english romaji }
    description
    genres
    tags { name rank }
  }
}
"""

def get_conn():
    return psycopg2.connect(
        dbname="animedb", user="postgres",
        password=os.environ.get("PG_PASSWORD"),
        host="localhost", port="5432"
    )

def fetch_anime(anime_id):
    response = requests.post(
        URL,
        json={"query": QUERY, "variables": {"id": anime_id}}
    )
    result = response.json()
    if result.get("data") is None or result["data"]["Media"] is None:
        raise ValueError(f"No data for ID {anime_id}. Response: {result}")
    return result["data"]["Media"]

def store_anime(media, embedding):
    title = media["title"]["english"] or media["title"]["romaji"]
    genres = json.dumps(media["genres"])
    tags = json.dumps([t["name"] for t in media["tags"]])
    description = media.get("description", "") or ""

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO titles (id, title, description, genres, tags)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
            SET title       = EXCLUDED.title,
                description = EXCLUDED.description,
                genres      = EXCLUDED.genres,
                tags        = EXCLUDED.tags
    """, (media["id"], title, description, genres, tags))

    cursor.execute("""
        INSERT INTO embeddings (id, vector)
        VALUES (%s, %s)
        ON CONFLICT (id) DO UPDATE
            SET vector = EXCLUDED.vector
    """, (media["id"], embedding.tolist()))

    conn.commit()
    conn.close()

anime_ids = [
    # Classics
    437,    # Cowboy Bebop
    6213,   # Trigun
    2167,   # Clannad
    889,    # Black Lagoon
    16,     # Trigun (alt id)
    19,     # Monster
    74,     # Planetes
    2904,   # Toradora
    2251,   # Baccano
    164,    # Mushi-Shi
    457,    # Fullmetal Alchemist
    47,     # Lovely Complex
    170,    # Elfen Lied
    572,    # Kino no Tabi
    1,      # Cowboy Bebop Movie (Knockin' on Heaven's Door)
    21,     # One Piece
    31,     # Neon Genesis Evangelion
    199,    # Sen to Chihiro (Spirited Away)
    523,    # Death Note
    9253,   # Steins;Gate
    11061,  # Hunter x Hunter 2011
    # 2020s titles
    145064, # Jujutsu Kaisen Season 2
    154587, # Frieren: Beyond Journey's End
    166531, # Dungeon Meshi
    163132, # Mushoku Tensei Season 2
    170942, # Solo Leveling
    158260, # Oshi no Ko
    149587, # Vinland Saga Season 2
    130003, # Chainsaw Man
    113415, # Spy x Family
    140960, # Blue Lock
    101922, # Kimetsu no Yaiba
    100526, # Violet Evergarden
    21856,  # Re:Zero
    97940,  # Made in Abyss
]

anime_ids = list(dict.fromkeys(anime_ids))
print(f"Embedding {len(anime_ids)} titles with BGE-base-en-v1.5 and rich tag expansion...\n")

for anime_id in anime_ids:
    try:
        media = fetch_anime(anime_id)
        soup = build_rich_soup(media)
        # normalize_embeddings=True ensures vectors are unit length,
        # which makes cosine similarity equivalent to dot product in FAISS
        embedding = model.encode(soup, normalize_embeddings=True)
        store_anime(media, embedding)
        title = media["title"]["english"] or media["title"]["romaji"]
        print(f"  Stored: {title}")
    except Exception as e:
        print(f"  Failed on ID {anime_id}: {e}")
    time.sleep(0.8)

print("\nDone.")
