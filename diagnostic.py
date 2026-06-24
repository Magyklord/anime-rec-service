import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(
        dbname="animedb", user="postgres",
        password=os.environ.get("PG_PASSWORD"),
        host="localhost", port="5432"
    )

HEADERS = {"User-Agent": "AnimeMatcher/1.0 (research project)"}
BASE = "https://arctic-shift.photon-reddit.com/api"

# Subreddits to search per title — ordered by relevance
SUBREDDITS = ["anime", "animerecommendations", "manga"]

# ── Load stored titles ───────────────────────────────────────────────────────
def load_titles():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM titles")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ── Fetch comments mentioning a title from a subreddit ──────────────────────
def fetch_comments(anime_title, subreddit, limit=100):
    """
    Fetches up to `limit` comments mentioning the title.
    We fetch a large batch because Arctic Shift sorts by time,
    not score — we do our own quality filtering in Python after.
    """
    try:
        response = requests.get(
            f"{BASE}/comments/search",
            headers=HEADERS,
            params={
                "body":      anime_title,
                "subreddit": subreddit,
                "limit":     str(limit),
                "sort_type": "created_utc"
            },
            timeout=10
        )
        if response.status_code != 200:
            return []
        return response.json().get("data", [])
    except Exception as e:
        print(f"  Request error: {e}")
        return []

# ── Filter for quality comments ──────────────────────────────────────────────
def filter_quality(comments, min_score=25, min_length=150):
    """
    Arctic Shift can't sort by score so we do it here.
    Keeps comments that are:
    - Upvoted enough to represent community consensus
    - Long enough to contain actual analysis
    - Not deleted or removed
    """
    quality = []
    for c in comments:
        body  = c.get("body", "")
        score = c.get("score", 0)

        if body in ("[deleted]", "[removed]", ""):
            continue
        if score < min_score:
            continue
        if len(body) < min_length:
            continue

        quality.append({"body": body, "score": score})

    # Sort best first — we'll store the top N
    quality.sort(key=lambda x: x["score"], reverse=True)
    return quality

# ── Store a critique with duplicate guard ────────────────────────────────────
def store_critique(title_id, body, score):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1 FROM critiques WHERE title_id = %s AND comment = %s
    """, (title_id, body))

    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO critiques (title_id, comment, upvotes)
        VALUES (%s, %s, %s)
    """, (title_id, body, score))

    conn.commit()
    conn.close()
    return True

# ── Main harvest loop ────────────────────────────────────────────────────────
def harvest():
    stored_titles = load_titles()
    print(f"Loaded {len(stored_titles)} titles.\n")

    total_stored = 0

    for title_id, anime_title in stored_titles:
        print(f"── {anime_title}")
        title_total = 0

        for subreddit in SUBREDDITS:
            raw = fetch_comments(anime_title, subreddit, limit=100)
            quality = filter_quality(raw, min_score=25, min_length=150)

            newly_stored = 0
            for comment in quality[:6]:  # max 6 per subreddit per title
                if store_critique(title_id, comment["body"], comment["score"]):
                    newly_stored += 1
                    title_total += 1
                    total_stored += 1

            if newly_stored > 0:
                print(f"  r/{subreddit}: {newly_stored} critiques "
                      f"(best score: {quality[0]['score']})")

            time.sleep(0.8)

        if title_total == 0:
            print(f"  No quality critiques found")
        print()

    print(f"── Harvest complete ─────────────────────────────────")
    print(f"  Total critiques stored: {total_stored}")

# ── Show results ─────────────────────────────────────────────────────────────
def show_results():
    conn = get_conn()
    cursor = conn.cursor()

    # Coverage summary — which titles have critiques
    cursor.execute("""
        SELECT t.title, COUNT(c.id) as count
        FROM titles t
        LEFT JOIN critiques c ON c.title_id = t.id
        GROUP BY t.title
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()

    print("\n── Critique coverage ────────────────────────────────")
    for title, count in rows:
        bar = "█" * count
        print(f"  {title:<45} {count:>3}  {bar}")

    # Best single critique we have
    cursor.execute("""
        SELECT t.title, c.upvotes, c.comment
        FROM critiques c
        JOIN titles t ON t.id = c.title_id
        ORDER BY c.upvotes DESC
        LIMIT 1
    """)
    best = cursor.fetchone()
    conn.close()

    if best:
        title, upvotes, comment = best
        print(f"\n── Highest upvoted critique ─────────────────────────")
        print(f"  [{upvotes:,} upvotes] {title}")
        print(f"  {comment[:300]}...")

if __name__ == "__main__":
    harvest()
    show_results()