import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, request, jsonify, render_template
from recommend import AnimeRecommender

app = Flask(__name__)

print("Loading model and index...", end="", flush=True)
rec = AnimeRecommender()
print(f" ready. ({rec.total} titles indexed)\n")
print("Server running at http://127.0.0.1:5000")

@app.route("/")
def index():
    return render_template("index.html", title_count=rec.total)

@app.route("/search", methods=["POST"])
def search():
    data   = request.get_json(force=True)
    query  = (data.get("query") or "").strip()
    top_n  = min(max(int(data.get("top_n", 5)), 1), 25)

    if not query:
        return jsonify([])

    results = rec.recommend(query, top_n=top_n, candidate_pool=30)
    return jsonify(results)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
