"""
Flask API server for H-RAG chat interface.
Exposes the query engine and system prompt management as REST endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from src.config import validate_config
from src.query import query_hrag, load_system_prompt, save_system_prompt

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/query", methods=["POST"])
def api_query():
    """Handle a chat query through the H-RAG pipeline."""
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' field"}), 400

    user_query = data["query"].strip()
    if not user_query:
        return jsonify({"error": "Empty query"}), 400
        
    nodes = data.get("nodes", ["anthropic", "projects"])

    try:
        result = query_hrag(user_query, nodes=nodes)

        # Build source references
        sources = []
        for chunk in result["retrieval"].get("chunks", []):
            meta = chunk.get("metadata", {})
            sources.append({
                "file": meta.get("file_name", "unknown"),
                "folder": meta.get("folder", ""),
                "similarity": round(chunk.get("similarity", 0), 3),
            })

        # Deduplicate sources by file name
        seen = set()
        unique_sources = []
        for s in sources:
            if s["file"] not in seen:
                seen.add(s["file"])
                unique_sources.append(s)

        return jsonify({
            "answer": result["answer"],
            "sources": unique_sources,
            "retrieval_path": {
                "folders": len(result["retrieval"].get("matched_folders", [])),
                "documents": len(result["retrieval"].get("matched_files", [])),
                "chunks": len(result["retrieval"].get("chunks", [])),
            },
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system-prompt", methods=["GET"])
def get_system_prompt():
    """Get the current system prompt."""
    try:
        prompt = load_system_prompt()
        return jsonify({"prompt": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system-prompt", methods=["POST"])
def set_system_prompt():
    """Update the system prompt."""
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing 'prompt' field"}), 400

    prompt = data["prompt"].strip()
    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    try:
        save_system_prompt(prompt)
        return jsonify({"status": "ok", "message": "System prompt updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "H-RAG API is running"})


if __name__ == "__main__":
    validate_config()
    print("\n>>> H-RAG Chat Server running at http://localhost:5000\n")
    app.run(debug=True, port=5000)
