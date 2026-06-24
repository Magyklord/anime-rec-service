import sys
import requests
import psycopg2
import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tag_expander import build_rich_soup

load_dotenv()

# ── Logging: writes to file AND prints to terminal ───────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("logs/paginator.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────
ANILIST_URL   = "https://graphql.anilist.co"
PAGES         = 100         # 100 × 50 = 5,000 anime total
PER_PAGE      = 50          # AniList's max per request
EMBED_BATCH   = 32          # how many texts to embed at once (speed)
PAGE_DELAY    = 1.2         # seconds between API pages  (≈50 req/min, well under 90/min limit)

# Sort order — pass "score" as a command-line argument to run the acclaimed pass:
#   python paginator.py           → POPULARITY_DESC  (most-watched first)
#   python paginator.py score     → SCORE_DESC        (highest-rated first)
SORT = "SCORE_DESC" if (len(sys.argv) > 1 and sys.argv[1].lower() == "score") else "POPULARITY_DESC"

# ── Model ─────────────────────────────────────────────────────────────────────
log.info("Loading embedding model...")
model = SentenceTransformer("BAAI/bge-base-en-v1.5")
log.info("Model ready.")

# ── AniList query ─────────────────────────────────────────────────────────────
# Sort order is injected from the SORT constant above.
# isAdult: false keeps the results clean.
PAGE_QUERY = f"""
query ($page: Int, $perPage: Int) {{
  Page(page: $page, perPage: $perPage) {{
    pageInfo {{ hasNextPage total currentPage }}
    media(type: ANIME, sort: {SORT}, isAdult: false) {{
      id
      title {{ english romaji }}
      description
      genres
      tags {{ name rank }}
      averageScore
      popularity
    }}
  }}
}}
"""

def get_conn():
    return psycopg2.connect(
        dbname="animedb",
        user="postgres",
        password=os.environ.get("PG_PASSWORD"),
        host="localhost",
        port="5432",
    )

def existing_ids() -> set:
    """Return the set of anime IDs already embedded in the database."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM embeddings")
    ids = {row[0] for row in cur.fetchall()}
    conn.close()
    return ids

def fetch_page(page: int) -> dict:
    """
    Fetch one page of 50 anime from AniList.
    Retries automatically if rate-limited (HTTP 429).
    """
    while True:
        try:
            resp = requests.post(
                ANILIST_URL,
                json={"query": PAGE_QUERY, "variables": {"page": page, "perPage": PER_PAGE}},
                timeout=15,
            )
        except requests.RequestException as e:
            log.warning(f"Network error on page {page}: {e}. Retrying in 10s...")
            time.sleep(10)
            continue

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            log.warning(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            log.error(f"Unexpected HTTP {resp.status_code} on page {page}. Skipping.")
            return None

        data = resp.json().get("data")
        if not data:
            log.error(f"No data field on page {page}: {resp.text[:200]}")
            return None

        return data["Page"]

def store_batch(media_list: list, embeddings) -> None:
    """Write a batch of anime + their embedding vectors in one DB transaction."""
    conn = get_conn()
    cur = conn.cursor()

    for media, vec in zip(media_list, embeddings):
        title = media["title"]["english"] or media["title"]["romaji"]

        cur.execute("""
            INSERT INTO titles
                (id, title, description, genres, tags, average_score, popularity)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title         = EXCLUDED.title,
                description   = EXCLUDED.description,
                genres        = EXCLUDED.genres,
                tags          = EXCLUDED.tags,
                average_score = EXCLUDED.average_score,
                popularity    = EXCLUDED.popularity
        """, (
            media["id"],
            title,
            media.get("description") or "",
            json.dumps(media["genres"]),
            json.dumps([t["name"] for t in media["tags"]]),
            media.get("averageScore"),
            media.get("popularity"),
        ))

        cur.execute("""
            INSERT INTO embeddings (id, vector)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET vector = EXCLUDED.vector
        """, (media["id"], vec.tolist()))

    conn.commit()
    conn.close()

def run():
    known = existing_ids()
    log.info(f"Starting paginator  [sort={SORT}]. {len(known)} titles already in database.")
    log.info(f"Target: {PAGES} pages × {PER_PAGE} anime = up to {PAGES * PER_PAGE} titles.\n")

    new_total = 0

    for page_num in range(1, PAGES + 1):
        log.info(f"── Page {page_num}/{PAGES} ────────────────────────────────")

        page_data = fetch_page(page_num)
        if page_data is None:
            time.sleep(PAGE_DELAY)
            continue

        all_media  = page_data["media"]
        new_media  = [m for m in all_media if m["id"] not in known]
        skip_count = len(all_media) - len(new_media)

        log.info(f"   Fetched {len(all_media)}  |  new: {len(new_media)}  |  skipped (exists): {skip_count}")

        if not new_media:
            time.sleep(PAGE_DELAY)
            continue

        # Build enriched text for every new anime on this page
        soups = [build_rich_soup(m) for m in new_media]

        # Embed in sub-batches — faster than one at a time
        for start in range(0, len(soups), EMBED_BATCH):
            sub_soups  = soups[start : start + EMBED_BATCH]
            sub_media  = new_media[start : start + EMBED_BATCH]

            vecs = model.encode(
                sub_soups,
                normalize_embeddings=True,
                batch_size=EMBED_BATCH,
                show_progress_bar=False,
            )

            store_batch(sub_media, vecs)

            for m in sub_media:
                t = m["title"]["english"] or m["title"]["romaji"]
                log.info(f"   + {t}")

            new_total += len(sub_media)
            known.update(m["id"] for m in sub_media)

        log.info(f"   Page done. Running new total: {new_total}\n")

        if not page_data["pageInfo"]["hasNextPage"]:
            log.info("AniList has no further pages.")
            break

        time.sleep(PAGE_DELAY)

    log.info(f"══ Paginator finished. {new_total} new titles added to database. ══")

if __name__ == "__main__":
    run()
