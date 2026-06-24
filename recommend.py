import sys
import psycopg2
import numpy as np
import faiss
import json
import os
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Force UTF-8 on Windows so titles with Unicode characters print correctly
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# BGE retrieval instruction: signals to the model that this text is a search
# query, not a document. BGE was trained to treat prefixed queries differently
# from stored passages, which improves matching when the words don't overlap.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# How much each signal contributes to the final score.
# Embedding captures vibe/mood; tag overlap captures structural match.
# 0.70/0.30 gives tag signal enough weight to meaningfully re-rank after
# score normalisation (previously tag score was too weak at 0.25).
EMBEDDING_WEIGHT = 0.70
TAG_WEIGHT       = 0.30

# Maps natural user language to canonical AniList tag/genre names.
# This bridges the gap between how fans describe anime and how AniList
# categorises it — e.g. "seas" → Pirates, "jazz" → Music + Melancholy.
QUERY_SYNONYMS = {
    "jazz":        ["Music", "Melancholy", "Noir", "Drama"],
    "blues":       ["Music", "Melancholy", "Noir", "Drama"],
    "soul":        ["Music", "Melancholy", "Drama"],
    "melancholic": ["Melancholy", "Tragedy", "Drama"],
    "melancholy":  ["Melancholy", "Tragedy", "Drama", "Noir"],
    "sad":         ["Melancholy", "Tragedy", "Grief"],
    "gloomy":      ["Melancholy", "Dark Themes"],
    "bittersweet": ["Melancholy", "Tragedy"],
    "sea":         ["Pirates", "Adventure"],
    "seas":        ["Pirates", "Adventure"],
    "ocean":       ["Pirates", "Adventure"],
    "ship":        ["Pirates", "Adventure"],
    "sailing":     ["Pirates", "Adventure"],
    "pirate":      ["Pirates"],
    "pirates":     ["Pirates"],
    "wander":      ["Anti-Hero", "Isolation"],
    "wanderer":    ["Anti-Hero", "Isolation"],
    "wandering":   ["Anti-Hero", "Isolation"],
    "drifter":     ["Anti-Hero", "Isolation", "Bounty Hunter"],
    "lone":        ["Anti-Hero", "Isolation"],
    "lonely":      ["Isolation", "Melancholy"],
    "loner":       ["Anti-Hero", "Isolation"],
    "haunted":     ["Psychological Trauma", "Grief"],
    "haunting":    ["Psychological Trauma", "Melancholy"],
    "regret":      ["Psychological Trauma", "Grief", "Redemption"],
    "past":        ["Psychological Trauma", "Amnesia"],
    "trauma":      ["Psychological Trauma", "Dark Themes"],
    "grief":       ["Grief", "Tragedy"],
    "loss":        ["Grief", "Tragedy"],
    "moral":       ["Philosophy", "Anti-Hero"],
    "morality":    ["Philosophy", "Anti-Hero"],
    "ambiguity":   ["Philosophy", "Anti-Hero"],
    "ambiguous":   ["Philosophy", "Anti-Hero"],
    "stakes":      ["Thriller", "War", "Survival"],
    "tension":     ["Thriller", "Psychological"],
    "suspense":    ["Thriller", "Mystery"],
    "bounty":      ["Bounty Hunter"],
    "hunter":      ["Bounty Hunter"],
    "detective":   ["Mystery", "Noir"],
    "noir":        ["Noir", "Mystery"],
    "robot":       ["Mecha"],
    "mech":        ["Mecha"],
    "sword":       ["Swordplay", "Samurai"],
    "samurai":     ["Samurai", "Historical"],
    "ninja":       ["Ninja", "Historical"],
    "friendship":  ["Found Family", "Friendship"],
    "friends":     ["Friendship", "Found Family"],
    "family":      ["Found Family"],
    "adventure":   ["Adventure"],
    "quest":       ["Adventure", "Fantasy"],
    "space":       ["Space", "Sci-Fi"],
    "cosmic":      ["Space", "Sci-Fi"],
    "futuristic":  ["Sci-Fi", "Space"],
    "magic":       ["Magic", "Fantasy"],
    "supernatural":["Supernatural"],
    "horror":      ["Horror", "Dark Themes"],
    "scary":       ["Horror"],
    "dark":        ["Dark Themes"],
    "romance":     ["Romance"],
    "love":        ["Romance"],
    "heartbreak":  ["Romance", "Tragedy"],
    "school":      ["High School"],
    "sport":       ["Sports"],
    "sports":      ["Sports"],
    "political":   ["Politics"],
    "war":         ["War", "Military"],
    "battle":      ["War", "Action"],
    "survival":    ["Survival"],
    "isekai":      ["Isekai"],
    "reincarnation":["Reincarnation", "Isekai"],
    "philosophy":  ["Philosophy"],
    "existential": ["Philosophy", "Psychological"],
    "psychological":["Psychological"],
    "mindbending": ["Psychological", "Philosophy"],
    "mystery":     ["Mystery"],
    "crime":       ["Mystery", "Noir"],
    "comedy":      ["Comedy"],
    "funny":       ["Comedy"],
    "wholesome":   ["Wholesome", "Slice of Life"],
    "healing":     ["Healing", "Slice of Life"],
    "slice":       ["Slice of Life"],
    "music":       ["Music"],
    "idol":        ["Idols", "Music"],
    "cyberpunk":   ["Cyberpunk", "Sci-Fi"],
    "dystopia":    ["Sci-Fi", "Post-Apocalyptic"],
    "apocalypse":  ["Post-Apocalyptic"],
    "historical":  ["Historical"],
    "period":      ["Historical"],
    "coming":      ["Coming of Age"],
    "growth":      ["Coming of Age"],
    "revenge":     ["Revenge"],
    "redemption":  ["Redemption"],
    "tragedy":     ["Tragedy"],
    "tragic":      ["Tragedy", "Grief"],
    "gore":        ["Gore", "Dark Themes"],
    "violent":     ["Gore", "Action"],
}

def get_conn():
    return psycopg2.connect(
        dbname="animedb",
        user="postgres",
        password=os.environ.get("PG_PASSWORD"),
        host="localhost",
        port="5432",
    )

def load_index():
    """Pull every stored vector from PostgreSQL and build a FAISS index."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, vector FROM embeddings ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("No embeddings found. Run paginator.py or fetch_and_embed.py first.")

    ids     = [row[0] for row in rows]
    vectors = [row[1] for row in rows]

    matrix = np.array(vectors, dtype="float32")
    faiss.normalize_L2(matrix)

    index = faiss.IndexFlatIP(768)   # 768 = BGE-base-en-v1.5 output size
    index.add(matrix)

    return index, ids

def load_metadata(ids: list) -> dict:
    """Fetch title, genres, tags, and score for a list of anime IDs."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, genres, tags, average_score, popularity FROM titles WHERE id = ANY(%s)",
        (ids,),
    )
    rows = cur.fetchall()
    conn.close()

    return {
        row[0]: {
            "title":   row[1],
            "genres":  json.loads(row[2]) if row[2] else [],
            "tags":    json.loads(row[3]) if row[3] else [],
            "score":   row[4] or 0,
            "pop":     row[5] or 0,
        }
        for row in rows
    }

def extract_query_keywords(query_text: str) -> set:
    """
    Pull meaningful words from the user's query to compare against tag/genre names.
    Strips common filler words so only content words remain.
    """
    stopwords = {
        "a","an","the","and","or","but","in","on","at","to","for",
        "with","by","of","from","is","are","was","were","be","been",
        "i","want","something","like","show","anime","series","story",
    }
    words = re.sub(r"[^a-z0-9 ]", " ", query_text.lower()).split()
    return {w for w in words if w not in stopwords and len(w) > 2}

def normalize_scores(score_dict: dict) -> dict:
    """
    Min-max normalise a dict of scores to [0, 1] within the candidate pool.
    Converts a tight cluster like 0.499–0.511 into a meaningful 0.0–1.0 spread
    so the tag component can actually influence the final ranking.
    """
    vals = list(score_dict.values())
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {k: 1.0 for k in score_dict}
    return {k: (v - lo) / (hi - lo) for k, v in score_dict.items()}

def tag_overlap_score(meta: dict, query_keywords: set) -> float:
    """
    Returns 0.0–1.0 based on how many query keywords, after synonym expansion,
    match the anime's actual AniList genres and tags.

    Example: query keyword "seas" → expands to ["Pirates", "Adventure"] →
    One Piece has both → score reflects those matches.
    """
    if not query_keywords:
        return 0.0

    # Expand each query keyword into canonical AniList terms
    canonical = set()
    for kw in query_keywords:
        canonical.update(QUERY_SYNONYMS.get(kw, [kw]))

    # Anime's actual genre and tag labels (exact AniList names)
    anime_labels = set(meta.get("genres", [])) | set(meta.get("tags", []))

    matches = len(canonical & anime_labels)
    return min(matches / max(len(query_keywords), 1), 1.0)

def recommend(query_text: str, top_n: int = 5, candidate_pool: int = 20):
    """
    Two-stage recommendation:
      1. FAISS retrieves the top `candidate_pool` by embedding similarity.
      2. Hybrid scorer re-ranks those candidates by blending embedding
         similarity with tag overlap, then returns the top `top_n`.
    """
    index, ids = load_index()

    # Encode the user query with the BGE instruction prefix
    prefixed = BGE_QUERY_PREFIX + query_text
    q_vec    = model.encode(prefixed, normalize_embeddings=True)
    q_mat    = np.array([q_vec], dtype="float32")
    faiss.normalize_L2(q_mat)

    # Stage 1: fast embedding search over the full database
    scores, positions = index.search(q_mat, min(candidate_pool, len(ids)))
    candidate_ids    = [ids[pos] for pos in positions[0]]
    embedding_scores = {ids[pos]: float(sc) for pos, sc in zip(positions[0], scores[0])}

    # Stage 2: normalise embedding scores, then load metadata and re-rank
    norm_embed     = normalize_scores(embedding_scores)
    meta_map       = load_metadata(candidate_ids)
    query_keywords = extract_query_keywords(query_text)

    ranked = []
    for anime_id in candidate_ids:
        meta    = meta_map.get(anime_id, {})
        e_norm  = norm_embed.get(anime_id, 0.0)
        e_raw   = embedding_scores.get(anime_id, 0.0)
        t_score = tag_overlap_score(meta, query_keywords)
        hybrid  = EMBEDDING_WEIGHT * e_norm + TAG_WEIGHT * t_score
        ranked.append((anime_id, hybrid, e_raw, t_score, meta))

    ranked.sort(key=lambda x: x[1], reverse=True)

    print(f"\nQuery: '{query_text}'\n")
    print(f"  {'Title':<45} {'Hybrid':>7}  {'Embed':>7}  {'Tags':>6}")
    print(f"  {'-'*45} {'-'*7}  {'-'*7}  {'-'*6}")
    for anime_id, hybrid, e_sc, t_sc, meta in ranked[:top_n]:
        title = meta.get("title", "Unknown")
        print(f"  {title:<45} {hybrid:>7.3f}  {e_sc:>7.3f}  {t_sc:>6.3f}")
    print()

def diagnose(query_text: str):
    """
    Shows every title in the database ranked by hybrid score.
    Use this to audit whether rankings make intuitive sense.
    """
    index, ids = load_index()

    prefixed = BGE_QUERY_PREFIX + query_text
    q_vec    = model.encode(prefixed, normalize_embeddings=True)
    q_mat    = np.array([q_vec], dtype="float32")
    faiss.normalize_L2(q_mat)

    scores, positions = index.search(q_mat, len(ids))
    candidate_ids    = [ids[pos] for pos in positions[0]]
    embedding_scores = {ids[pos]: float(sc) for pos, sc in zip(positions[0], scores[0])}

    norm_embed     = normalize_scores(embedding_scores)
    meta_map       = load_metadata(candidate_ids)
    query_keywords = extract_query_keywords(query_text)

    ranked = []
    for anime_id in candidate_ids:
        meta    = meta_map.get(anime_id, {})
        e_norm  = norm_embed.get(anime_id, 0.0)
        e_raw   = embedding_scores.get(anime_id, 0.0)
        t_score = tag_overlap_score(meta, query_keywords)
        hybrid  = EMBEDDING_WEIGHT * e_norm + TAG_WEIGHT * t_score
        ranked.append((anime_id, hybrid, e_raw, t_score, meta))

    ranked.sort(key=lambda x: x[1], reverse=True)

    print(f"\nFull ranking for: '{query_text}'\n")
    print(f"  {'#':>2}  {'Title':<45} {'Hybrid':>7}  {'Embed':>7}  {'Tags':>6}")
    print(f"  {'--':>2}  {'-'*45} {'-'*7}  {'-'*7}  {'-'*6}")
    for rank, (anime_id, hybrid, e_sc, t_sc, meta) in enumerate(ranked, 1):
        title = meta.get("title", "Unknown")
        bar   = "█" * int(hybrid * 40)
        print(f"  {rank:>2}.  {title:<45} {hybrid:.4f}  {e_sc:.4f}  {t_sc:.4f}  {bar}")
    print()

class AnimeRecommender:
    """
    Loads the FAISS index, all vectors, and all title metadata once at startup.
    Every subsequent query is a pure in-memory operation — no database round-trip.
    """

    def __init__(self):
        self.index, self.ids = load_index()
        # Preload metadata for every title so queries never hit the DB again
        self.meta_map = load_metadata(self.ids)
        self.total    = len(self.ids)

    def _search(self, query_text: str, n: int):
        prefixed = BGE_QUERY_PREFIX + query_text
        q_vec    = model.encode(prefixed, normalize_embeddings=True)
        q_mat    = np.array([q_vec], dtype="float32")
        faiss.normalize_L2(q_mat)

        scores, positions = self.index.search(q_mat, min(n, self.total))
        candidate_ids    = [self.ids[pos] for pos in positions[0]]
        embedding_scores = {self.ids[pos]: float(sc) for pos, sc in zip(positions[0], scores[0])}
        return candidate_ids, embedding_scores

    def _rank(self, candidate_ids, embedding_scores, query_text):
        norm_embed     = normalize_scores(embedding_scores)
        query_keywords = extract_query_keywords(query_text)
        ranked = []
        for anime_id in candidate_ids:
            meta    = self.meta_map.get(anime_id, {})
            e_norm  = norm_embed.get(anime_id, 0.0)
            e_raw   = embedding_scores.get(anime_id, 0.0)
            t_score = tag_overlap_score(meta, query_keywords)
            hybrid  = EMBEDDING_WEIGHT * e_norm + TAG_WEIGHT * t_score
            ranked.append({
                "id":      anime_id,
                "hybrid":  hybrid,
                "embed":   e_raw,
                "tags":    t_score,
                "title":   meta.get("title", "Unknown"),
                "genres":  meta.get("genres", []),
                "score":   meta.get("score", 0),
            })
        ranked.sort(key=lambda x: x["hybrid"], reverse=True)
        return ranked

    def recommend(self, query_text: str, top_n: int = 5, candidate_pool: int = 20):
        ids, scores = self._search(query_text, candidate_pool)
        return self._rank(ids, scores, query_text)[:top_n]

    def diagnose(self, query_text: str):
        ids, scores = self._search(query_text, self.total)
        return self._rank(ids, scores, query_text)


if __name__ == "__main__":
    recommend("lonely wanderer haunted by the past, jazz and melancholy")
    recommend("psychological thriller with moral ambiguity and high stakes")
    recommend("friendship and adventure on the high seas")
    diagnose("friendship and adventure on the high seas")
