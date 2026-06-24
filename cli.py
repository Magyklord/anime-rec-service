import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from recommend import AnimeRecommender

BANNER = """\
╔══════════════════════════════════════════════════════════════╗
║              Anime Recommendation Engine                    ║
╚══════════════════════════════════════════════════════════════╝"""

HELP_TEXT = """\
  How to search:
    Type any mood, vibe, or description and press Enter.

  Examples:
    lonely wanderer haunted by the past, jazz and melancholy
    psychological thriller with moral ambiguity and high stakes
    friendship and adventure on the high seas
    cute slice of life healing anime
    dark fantasy with war and political intrigue

  Commands:
    /top <n>    show top N results for the last query   (e.g. /top 10)
    /diagnose   show full ranked list for the last query
    /help       show this message
    /quit       exit\
"""

def _bar(score: float, width: int = 20) -> str:
    return "█" * int(score * width)

def print_results(results: list, query_text: str) -> None:
    print(f"\n  Results for: \"{query_text}\"\n")
    print(f"  {'#':>2}  {'Title':<44}  {'Match':>5}  Genres")
    print(f"  {'─'*2}  {'─'*44}  {'─'*5}  {'─'*34}")
    for i, r in enumerate(results, 1):
        title  = r["title"][:44]
        hybrid = r["hybrid"]
        genres = "  ·  ".join(r["genres"][:3])
        bar    = _bar(hybrid)
        print(f"  {i:>2}.  {title:<44}  {hybrid:>5.3f}  {genres}")
    print()

def print_diagnose(results: list, query_text: str) -> None:
    print(f"\n  Full ranking for: \"{query_text}\"\n")
    print(f"  {'#':>3}  {'Title':<44}  {'Hybrid':>6}  {'Embed':>6}  {'Tags':>5}  Chart")
    print(f"  {'─'*3}  {'─'*44}  {'─'*6}  {'─'*6}  {'─'*5}  {'─'*20}")
    for i, r in enumerate(results, 1):
        title = r["title"][:44]
        bar   = _bar(r["hybrid"])
        print(
            f"  {i:>3}.  {title:<44}  {r['hybrid']:>6.3f}"
            f"  {r['embed']:>6.3f}  {r['tags']:>5.3f}  {bar}"
        )
    print()

def run_command(cmd_line: str, rec: AnimeRecommender, last_query: str | None) -> str | None:
    """
    Process a slash command. Returns the last_query unchanged (commands don't update it).
    Prints output directly.
    """
    parts = cmd_line.strip().split()
    cmd   = parts[0].lower()

    if cmd in ("/quit", "/exit", "/q"):
        print("\n  Goodbye.\n")
        sys.exit(0)

    elif cmd == "/help":
        print(f"\n{HELP_TEXT}\n")

    elif cmd == "/top":
        if last_query is None:
            print("\n  No previous query — type a search first.\n")
            return last_query
        n = 10
        if len(parts) > 1:
            try:
                n = max(1, int(parts[1]))
            except ValueError:
                print(f"\n  Usage: /top <number>    e.g. /top 10\n")
                return last_query
        results = rec.recommend(last_query, top_n=n, candidate_pool=max(n * 2, 20))
        print_results(results, last_query)

    elif cmd == "/diagnose":
        if last_query is None:
            print("\n  No previous query — type a search first.\n")
            return last_query
        print("\n  Running full ranking (may take a moment)...", end="", flush=True)
        results = rec.diagnose(last_query)
        print(f"\r{' ' * 50}\r", end="")   # clear the "Running..." line
        print_diagnose(results, last_query)

    else:
        print(f"\n  Unknown command '{cmd}'.  Type /help for usage.\n")

    return last_query

def main() -> None:
    print(f"\n{BANNER}")
    print("\n  Loading model and index...", end="", flush=True)

    try:
        rec = AnimeRecommender()
    except RuntimeError as e:
        print(f"\n\n  Error: {e}")
        print("  Run setup_pg.py and fetch_and_embed.py first.\n")
        sys.exit(1)

    print(f" ready.  ({rec.total} titles indexed)\n")
    print(HELP_TEXT)
    print("\n" + "─" * 64 + "\n")

    last_query: str | None = None

    while True:
        try:
            raw = input("  › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.\n")
            break

        if not raw:
            continue

        if raw.startswith("/"):
            last_query = run_command(raw, rec, last_query)
            continue

        # Regular search query
        last_query = raw
        try:
            results = rec.recommend(raw, top_n=5, candidate_pool=20)
            print_results(results, raw)
            print("  ↳  /top 10 for more  ·  /diagnose for full ranking\n")
        except Exception as e:
            print(f"\n  Error during search: {e}\n")

if __name__ == "__main__":
    main()
