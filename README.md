# Anime Recommendation Engine

A semantic anime recommendation service that lets you search by mood, vibe, or description — not just title. It uses a hybrid scoring system combining sentence embeddings and AniList tag matching to find anime that actually fit what you're looking for.

## How it works

1. **Data** — Pulls 5,000+ anime from the [AniList GraphQL API](https://anilist.co) with genres, tags, scores, and descriptions.
2. **Embeddings** — Each anime is converted into a 768-dimensional vector using `BAAI/bge-base-en-v1.5`, a sentence embedding model. The raw AniList data is first expanded into rich viewer-experience language before embedding (see `tag_expander.py`).
3. **Storage** — Titles and vectors are stored in a local PostgreSQL database.
4. **Search** — At query time, FAISS retrieves the top candidates by embedding similarity, then a hybrid scorer re-ranks them by blending semantic similarity (70%) with AniList tag overlap (30%).

## Example queries

```
lonely wanderer haunted by the past, jazz and melancholy
psychological thriller with moral ambiguity and high stakes
friendship and adventure on the high seas
cute slice of life healing anime
dark fantasy with war and political intrigue
```

## Stack

- **Python 3.11+**
- **Flask** — web UI
- **PostgreSQL** — stores titles and embedding vectors
- **FAISS** — fast nearest-neighbour vector search
- **sentence-transformers** — `BAAI/bge-base-en-v1.5` for embeddings
- **AniList GraphQL API** — anime metadata source

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally on port 5432 with a `postgres` user

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```
PG_PASSWORD=your_postgres_password
```

### 4. Restore the database

A pre-built database dump (`animedb_dump.zip`) is included in the repo with 5,000+ titles already fetched and embedded. Restore it with:

```bash
python restore_db.py
```

This extracts the zip, creates the `animedb` database, loads all the data, and cleans up. Takes about a minute.

### (Optional) Re-fetch data from scratch

If you want to rebuild the database yourself instead of using the dump:

```bash
python setup_pg.py
python paginator.py
```

`paginator.py` fetches 100 pages × 50 anime from AniList and generates embeddings — takes roughly 20–30 minutes. Pass `score` as an argument to sort by rating instead of popularity:

```bash
python paginator.py score
```

## Running

### Web UI

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### CLI

```bash
python cli.py
```

Commands inside the CLI:

| Command | Description |
|---|---|
| `<any text>` | Search by mood or description |
| `/top <n>` | Show top N results for the last query |
| `/diagnose` | Show full ranked list with score breakdown |
| `/help` | Show help |
| `/quit` | Exit |

## Project structure

```
├── app.py            # Flask web server
├── cli.py            # Terminal interface
├── recommend.py      # Core recommendation engine (FAISS + hybrid scoring)
├── paginator.py      # AniList data fetcher and embedder
├── setup_pg.py       # Database and schema setup
├── tag_expander.py   # Expands AniList tags/genres into descriptive text
├── templates/
│   └── index.html    # Web UI
├── static/
│   └── style.css     # Styles
├── animedb_dump.zip  # Pre-built database dump (restore with restore_db.py)
├── restore_db.py     # One-command database restore for new users
├── requirements.txt
└── .env              # Not committed — see setup above
```
