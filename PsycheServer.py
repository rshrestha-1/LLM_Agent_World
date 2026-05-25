from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_PING = "http://localhost:11434"
MODEL       = "qwen2.5:0.5b"

SYSTEM_PROMPT = """You are Psyche, a mortal woman navigating dangerous trials set by the goddess Aphrodite.
You move through a 2D grid world. Each step you receive a JSON observation and must choose one action.

YOUR TRIALS:
- Task I:   Sort the grain with help from the ants before nightfall
- Task II:  Collect golden wool from brambles while the sun-rams sleep
- Task III: Fill your flask at the source of the Styx past the sleepless dragons
- Task IV:  Descend into the Underworld, retrieve Persephone's box, and return

WHAT THE SYMBOLS MEAN:
  @ you (Psyche)
  # wall or cliff face
  . passable floor
  K key item (ant helper / wool from bramble / river reed / coin or honeycake)
  D door (grain sack / ram pen gate / cliff gate / Underworld gate)
  C chest — your goal (sorted grain / golden fleece / Styx water / Persephone's box)
  ! hazard — avoid (grain pile / sun-ram / dragon / pleading soul)
  E exit — return to the surface or temple

ACTIONS (output ONE as a single JSON object, nothing else):
  {"action": "move", "params": {"direction": "north"}}
  {"action": "move", "params": {"direction": "south"}}
  {"action": "move", "params": {"direction": "east"}}
  {"action": "move", "params": {"direction": "west"}}
  {"action": "look", "params": {}}

RULES:
- Reply with ONLY the JSON object. No text before or after. No markdown.
- Collect K items by stepping on them - they go into your inventory automatically
- Step into a D door when you have a K in inventory — it opens automatically
- Reach C to achieve your goal
- Avoid ! hazard tiles — step around them
- Check nearby_items and adjacent_cells to plan your route
"""


def ollama_is_running():
    try:
        requests.get(OLLAMA_PING, timeout=2)
        return True
    except Exception:
        return False


def call_ollama(messages):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 40,
        }
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


@app.route("/agent", methods=["POST"])
def agent():
    if not ollama_is_running():
        msg = "Ollama not running. Run: ollama serve"
        print(f"[ERROR] {msg}")
        return jsonify({"error": msg}), 503
    try:
        data  = request.get_json()
        reply = call_ollama(data["messages"])
        print(f"[OK] {reply[:100]}")
        return jsonify({"content": reply})
    except requests.exceptions.Timeout:
        msg = f"Ollama timed out. Try: ollama pull qwen2.5:0.5b"
        print(f"[TIMEOUT] {msg}")
        return jsonify({"error": msg}), 504
    except Exception as e:
        print(f"[ERROR] /agent failed:")
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
        return jsonify({
            "status":  "model_missing",
            "message": f"Run: ollama pull {MODEL}",
            "available": names
        }), 503
    except Exception:
        return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("=" * 54)
    print("  Psyche and Cupid — Agent Server")
    print(f"  http://localhost:5001  |  model: {MODEL}")
    if ollama_is_running():
        print("  Ollama: RUNNING")
        try:
            r     = requests.get("http://localhost:11434/api/tags", timeout=3)
            names = [m["name"] for m in r.json().get("models", [])]
            print(f"  Models available: {names}")
            if not any(MODEL in n for n in names):
                print(f"\n  !! Pull the model first:  ollama pull {MODEL}")
        except Exception:
            pass
    else:
        print("  !! Ollama not running — run: ollama serve")
    print("=" * 54)
    app.run(host="0.0.0.0", port=5001, debug=False)