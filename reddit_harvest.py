import requests
import psycopg2
import os
import time
import json
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

# ── Load stored titles ───────────────────────────────────────────────────────
def load_titles():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM titles")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ── Match post title to stored anime ────────────────────────────────────────
def find_title_id(post_title, stored_titles):
    post_lower = post_title.lower()
    for title_id, title in stored_titles:
        if title and title.lower() in post_lower:
            return title_id, title
    return None, None

# ── Fetch posts mentioning a specific anime title ────────────────────────────
def fetch_posts(anime_title, subreddit="anime", limit=25):
    params = {
        "title": anime_title,
        "subreddit": subreddit,
        "limit": str(limit),
        "sort_type": "created_utc"
    }
    try:
        response = requests.get(
            f"{BASE}/posts/search",
            headers=HEADERS,
            params=params,
            timeout=10
        )
        if response.status_code != 200:
            print(f"  Posts fetch failed: HTTP {response.status_code}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        print(f"  Request error: {e}")
        return []

# ── Fetch comments mentioning a specific anime title ─────────────────────────
def fetch_comments(anime_title, subreddit="anime", limit=50):
    params = {
        "body": anime_title,
        "subreddit": subreddit,
        "limit": str(limit),
        "sort_type": "created_utc"
    }
    try:
        response = requests.get(
            f"{BASE}/comments/search",
            headers=HEADERS,
            params=params,
            timeout=10
        )
        if response.status_code != 200:
            print(f"  Comments fetch failed: HTTP {response.status_code}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        print(f"  Request error: {e}")
        return []

# ── Store a critique ─────────────────────────────────────────────────────────
def store_critique(title_id, comment_body, upvotes):
    conn = get_conn()
    cursor = conn.cursor()

    # Duplicate guard
    cursor.execute("""
        SELECT 1 FROM critiques WHERE title_id = %s AND comment = %s
    """, (title_id, comment_body))

    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO critiques (title_id, comment, upvotes)
        VALUES (%s, %s, %s)
    """, (title_id, comment_body, upvotes))

    conn.commit()
    conn.close()
    return True

# ── Main harvest loop ────────────────────────────────────────────────────────
def harvest():
    stored_titles = load_titles()
    print(f"Loaded {len(stored_titles)} titles.\n")

    # Subreddits to search per title
    subreddits = ["anime", "animerecommendations", "manga"]

    total_stored = 0

    for title_id, anime_title in stored_titles:
        print(f"── {anime_title} ──────────────────────────────")
        title_stored = 0

        for subreddit in subreddits:
            # Search comments directly — more targeted than post body
            comments = fetch_comments(anime_title, subreddit=subreddit, limit=50)

            # Filter for quality in Python since API can't sort by score
            quality = [
                c for c in comments
                if c.get("score", 0) >= 50        # upvote threshold
                and len(c.get("body", "")) >= 150  # length threshold
                and c.get("body") not in ("[deleted]", "[removed]")
            ]

            # Sort by score descending — best comments first
            quality.sort(key=lambda x: x.get("score", 0), reverse=True)

            newly_stored = 0
            for comment in quality[:8]:  # cap at 8 per subreddit
                if store_critique(title_id, comment["body"], comment["score"]):
                    newly_stored += 1
                    title_stored += 1
                    total_stored += 1

            if newly_stored > 0:
                print(f"  r/{subreddit}: stored {newly_stored} critiques")

            time.sleep(0.8)  # polite delay between requests

        if title_stored == 0:
            print(f"  No critiques found across any subreddit")
        print()

    print(f"── Harvest complete ──────────────────────────────────")
    print(f"  Total critiques stored: {total_stored}")

# ── Verify results ───────────────────────────────────────────────────────────
def show_stored_critiques():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.title, COUNT(c.id) as critique_count
        FROM titles t
        LEFT JOIN critiques c ON c.title_id = t.id
        GROUP BY t.title
        ORDER BY critique_count DESC
    """)
    rows = cursor.fetchall()

    print("\n── Critiques per title ───────────────────────────────")
    for title, count in rows:
        bar = "█" * count
        print(f"  {title:<45} {count:>3}  {bar}")

    # Show the single best critique we stored
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
        print(f"\n── Highest upvoted critique ──────────────────────────")
        print(f"  {title} [{upvotes:,} upvotes]")
        print(f"  {comment[:300]}...")

if __name__ == "__main__":
    harvest()
    show_stored_critiques()