from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_PING = "http://localhost:11434"
MODEL       = "qwen2.5:0.5b"

SYSTEM_PROMPT = """You are navigating a 2D grid. Output ONE JSON action per turn, nothing else.

ACTIONS:
{"action": "move", "params": {"direction": "north"}}
{"action": "move", "params": {"direction": "south"}}
{"action": "move", "params": {"direction": "east"}}
{"action": "move", "params": {"direction": "west"}}

RULES:
- Only move in a direction listed in passable_directions
- Use move_hint from nearby_items to navigate toward your goal
- Collect K by stepping on it
- Step into D with K in inventory to open it
- Reach C to win
- Output ONLY the JSON, nothing else
"""

def ollama_is_running():
    try:
        requests.get(OLLAMA_PING, timeout=2)
        return True
    except:
        return False

def call_ollama(messages):
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 40}
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]

@app.route("/agent", methods=["POST"])
def agent():
    if not ollama_is_running():
        return jsonify({"error": "Ollama not running. Run: ollama serve"}), 503
    try:
        data  = request.get_json()
        reply = call_ollama(data["messages"])
        print(f"[OK] {reply[:80]}")
        return jsonify({"content": reply})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Ollama timed out"}), 504
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/ping", methods=["GET"])
def ping():
    if not ollama_is_running():
        return jsonify({"status": "ollama_offline"}), 503
    try:
        r     = requests.get("http://localhost:11434/api/tags", timeout=3)
        names = [m["name"] for m in r.json().get("models", [])]
        if any(MODEL in n for n in names):
            return jsonify({"status": "ok", "model": MODEL})
        return jsonify({"status": "model_missing", "message": f"Run: ollama pull {MODEL}"}), 503
    except:
        return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("=" * 50)
    print(f"  Psyche — server on http://localhost:5001")
    print(f"  Model: {MODEL}")
    print(f"  Ollama: {'RUNNING' if ollama_is_running() else 'NOT FOUND'}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5001, debug=False)