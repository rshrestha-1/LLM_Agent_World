"""
agent_world.py
--------------
Terminal runner for the LLM agent.
Start server.py first, then run this.

Usage:
    python agent_world.py                     # scenario 0 (default)
    python agent_world.py --scenario 1
    python agent_world.py --scenario 2
    python agent_world.py --list-scenarios
    python agent_world.py --log run.json      # saves a JSON log
    python agent_world.py --quiet             # no verbose output
"""

import sys
import json
import time
import argparse
from dataclasses import dataclass, field, asdict
from typing import Optional
import requests

# ── Cell symbols ────────────────────────────────────────────
EMPTY  = "."
WALL   = "#"
AGENT  = "@"
KEY    = "K"
DOOR   = "D"
OPEN   = "O"
CHEST  = "C"
HAZARD = "!"
EXIT   = "E"

ENTITY_NAMES = {
    EMPTY:  "empty floor",
    WALL:   "wall",
    AGENT:  "you",
    KEY:    "KEY (pick this up)",
    DOOR:   "LOCKED DOOR (need a key)",
    OPEN:   "open doorway",
    CHEST:  "TREASURE CHEST (your goal!)",
    HAZARD: "HAZARD (avoid)",
    EXIT:   "EXIT (your goal!)",
}

DIRECTIONS = {
    "north": (0, -1),
    "south": (0,  1),
    "east":  (1,  0),
    "west":  (-1, 0),
}

# ── Data classes ─────────────────────────────────────────────

@dataclass
class AgentState:
    x: int
    y: int
    inventory: list = field(default_factory=list)
    steps: int = 0
    goal_achieved: bool = False
    hazard_hits: int = 0

@dataclass
class WorldConfig:
    name: str
    description: str
    grid: list
    start: tuple
    goal: str
    max_steps: int = 40

# ── Scenarios ─────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────
# PSYCHE SCENARIOS  —  paste this into agent_world.py
# replacing the existing SCENARIOS list
#
# Source: Apuleius, The Golden Ass (Metamorphoses), Books 4-6, c.160 AD
#
# Symbol mapping (same mechanics, new meaning per task):
#   K = key      Task1=ant, Task2=bramble, Task3=reed, Task4=coin/cake
#   D = door     Task1=grain bag, Task2=ram pen gate, Task3=dragon gate, Task4=Charon/Cerberus
#   C = chest    Task1=sorted pile, Task2=golden fleece, Task3=Styx water, Task4=Persephone's box
#   ! = hazard   Task1=unsorted grain pile, Task2=sun-rams, Task3=dragons, Task4=pleading souls
#   E = exit     Task1=temple door, Task2=meadow exit, Task3=cliff exit, Task4=return to surface
#   @ = Psyche (the agent)
# ─────────────────────────────────────────────────────────

SCENARIOS = [

    # ─────────────────────────────────────────────────────
    # TASK 1 — Sort the Grain
    # Aphrodite dumps a vast mixed pile of grain and sets
    # Psyche an impossible task. Ants (K) take pity and
    # help her. She must collect ant helpers then deposit
    # grain into the correct sacks (D) before nightfall.
    # ─────────────────────────────────────────────────────
    WorldConfig(
        name="Task I — The Grain Room",
        description="Aphrodite's first task: sort the grain before nightfall with help from the ants.",
        grid=[
            "####################",
            "#K.!..!...K.........#",
            "#....................#",
            "#....!...!...K......#",
            "#....................#",
            "#..!.....!...........#",
            "#....................#",
            "#...K.....!.....K...#",
            "#....................#",
            "#....!.....!........#",
            "#....................#",
            "#..K....!...........#",
            "#....................#",
            "##D###D###D###D######",
            "#....C..............#",
            "####################",
        ],
        start=(1, 1),
        goal=(
            "Collect ANT HELPERS (K) to guide you through the grain room. "
            "The scattered grain piles (!) will slow you — avoid them. "
            "Reach each GRAIN SACK (D) using an ant helper to sort the grain. "
            "Once all sacks are filled, reach the SORTED PILE (C) to complete the task."
        ),
        max_steps=60,
    ),

    # ─────────────────────────────────────────────────────
    # TASK 2 — The Golden Fleece
    # Violent sun-rams (!) graze the meadow. Psyche must
    # wait and collect wool from brambles (K) at the edge
    # while avoiding the rams. The fleece (C) waits at
    # the far side. Exit (E) returns to Aphrodite's temple.
    # ─────────────────────────────────────────────────────
    WorldConfig(
        name="Task II — The Golden Fleece",
        description="Aphrodite's second task: collect golden wool from the brambles while the sun-rams sleep.",
        grid=[
            "####################",
            "#@.................E#",
            "#..................K#",
            "#...!!!!!!!!!!!!....#",
            "#...!          !..K.#",
            "#...!  !!!!!!  !....#",
            "#...!  !    !  !....#",
            "#K..!  ! C  !  !....#",
            "#...!  !    !  !..K.#",
            "#...!  !!!!!!  !....#",
            "#...!          !....#",
            "#...!!!!!!!!!!!!....#",
            "#..................K#",
            "#..................K#",
            "#..............K....#",
            "####################",
        ],
        start=(1, 1),
        goal=(
            "The sun-rams (!) graze in the central meadow — do not approach them directly. "
            "Collect WOOL FROM BRAMBLES (K) caught on the hedges around the meadow edge. "
            "Once you have enough wool, find a path through to the GOLDEN FLEECE (C) at the centre. "
            "Then reach the EXIT (E) to return to Aphrodite's temple."
        ),
        max_steps=60,
    ),

    # ─────────────────────────────────────────────────────
    # TASK 3 — Water from the Styx
    # The cliff of the Styx is guarded by sleepless dragons.
    # A river reed (K) whispers guidance. Psyche must
    # navigate the cliff face, avoiding dragons (!),
    # using the reeds to find safe passages (D) through
    # the rock, to reach the source of the Styx (C).
    # ─────────────────────────────────────────────────────
    WorldConfig(
        name="Task III — The River Styx",
        description="Aphrodite's third task: fill the crystal flask at the source of the Styx, past the sleepless dragons.",
        grid=[
            "####################",
            "#@.................#",
            "#..................#",
            "#....K.............#",
            "#...........K......#",
            "####D###############",
            "#..................#",
            "#...!..............#",
            "#......!...........#",
            "#...........K......#",
            "####D###############",
            "#...!..............#",
            "#.........!........#",
            "#......K...........#",
            "####D###############",
            "#...!.....!........#",
            "#..........!.......#",
            "#..................#",
            "#.........C........#",
            "####################",
        ],
        start=(1, 1),
        goal=(
            "The cliff face drops to the source of the Styx. "
            "Sleepless DRAGONS (!) patrol each level — avoid them. "
            "Collect RIVER REEDS (K) which whisper the safe route through the rock gates. "
            "Use the reeds to pass through each CLIFF GATE (D). "
            "Reach the SOURCE OF THE STYX (C) and fill the crystal flask."
        ),
        max_steps=70,
    ),

    # ─────────────────────────────────────────────────────
    # TASK 4 — Descent into the Underworld
    # The most dangerous task. Psyche must navigate Hades,
    # collecting coins for Charon and honeycakes for
    # Cerberus (K), ignoring the pleading souls (!),
    # passing through each gate of the Underworld (D),
    # reaching Persephone's box (C), then returning
    # to the exit (E) — but she must not open the box.
    # ─────────────────────────────────────────────────────
    WorldConfig(
        name="Task IV — The Underworld",
        description="Aphrodite's fourth and final task: descend to Hades, retrieve Persephone's box of beauty, and return.",
        grid=[
            "####################",
            "#@.................#",
            "#...K..............#",
            "#.........K........#",
            "#..................#",
            "##########D#########",
            "#...!..............#",
            "#.......!..........#",
            "#...........K......#",
            "#..................#",
            "##########D#########",
            "#...!..............#",
            "#.......!..........#",
            "#..................#",
            "#.....K............#",
            "##########D#########",
            "#..................#",
            "#.......!..........#",
            "#.....C............#",
            "####################",
        ],
        start=(1, 1),
        goal=(
            "Descend into the Underworld to retrieve Persephone's box of beauty. "
            "Collect COINS AND HONEYCAKES (K) — you need them to pay Charon and appease Cerberus at each gate. "
            "The PLEADING SOULS (!) will try to slow you — ignore them and keep moving. "
            "Pass through each UNDERWORLD GATE (D) using your coins and cakes. "
            "Reach PERSEPHONE'S BOX (C) and take it. "
            "Then find the EXIT (E) back to the surface — and do NOT open the box."
        ),
        max_steps=80,
    ),

]

# ── World engine ──────────────────────────────────────────────

class World:
    def __init__(self, config: WorldConfig):
        self.config = config
        self.grid   = [list(row) for row in config.grid]
        self.height = len(self.grid)
        self.width  = max(len(r) for r in self.grid)
        for row in self.grid:
            while len(row) < self.width:
                row.append(" ")
        sx, sy = config.start
        self.grid[sy][sx] = AGENT
        self.agent = AgentState(x=sx, y=sy)
        self.done   = False
        self.result = None

    def cell(self, x, y):
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y][x]
        return WALL

    def set_cell(self, x, y, ch):
        self.grid[y][x] = ch

    def observe(self):
        ax, ay = self.agent.x, self.agent.y

        # 5x5 viewport centred on agent
        viewport_rows = []
        for dy in range(-2, 3):
            row = []
            for dx in range(-2, 3):
                row.append(self.cell(ax + dx, ay + dy))
            viewport_rows.append("".join(row))
        viewport_str = "\n".join(viewport_rows)

        # What is directly adjacent in each direction?
        adjacents = {}
        for dirn, (dx, dy) in DIRECTIONS.items():
            ch = self.cell(ax + dx, ay + dy)
            adjacents[dirn] = {
                "symbol":   ch,
                "name":     ENTITY_NAMES.get(ch, "unknown"),
                "passable": ch not in (WALL, DOOR, " "),
            }

        # Items within Manhattan distance 5
        nearby = []
        for iy in range(self.height):
            for ix in range(self.width):
                ch   = self.grid[iy][ix]
                dist = abs(ix - ax) + abs(iy - ay)
                if ch in (KEY, DOOR, CHEST, EXIT, HAZARD, OPEN) and dist <= 5:
                    nearby.append({
                        "symbol":     ch,
                        "name":       ENTITY_NAMES.get(ch, "?"),
                        "relative_x": ix - ax,
                        "relative_y": iy - ay,
                        "distance":   dist,
                    })
        nearby.sort(key=lambda i: i["distance"])

        return {
            "position":        {"x": ax, "y": ay},
            "inventory":       list(self.agent.inventory),
            "steps_taken":     self.agent.steps,
            "steps_remaining": self.config.max_steps - self.agent.steps,
            "goal":            self.config.goal,
            "viewport_5x5":    viewport_str,
            "legend":          "@ you  # wall  . floor  K key  D locked-door  O open-door  C chest  ! hazard  E exit",
            "adjacent_cells":  adjacents,
            "nearby_items":    nearby,
            "hazard_hits":     self.agent.hazard_hits,
        }

    def act(self, action, params):
        ax, ay = self.agent.x, self.agent.y

        if action == "move":
            direction = params.get("direction", "").strip().lower()
            if direction not in DIRECTIONS:
                return {"success": False, "message": f"Bad direction '{direction}'. Use north/south/east/west."}
            dx, dy = DIRECTIONS[direction]
            nx, ny = ax + dx, ay + dy
            target = self.cell(nx, ny)

            if target in (WALL, " "):
                return {"success": False, "message": "Blocked by a wall."}

            if target == DOOR:
                if KEY in self.agent.inventory:
                    self.agent.inventory.remove(KEY)
                    self.set_cell(nx, ny, OPEN)
                    self.set_cell(ax, ay, EMPTY)
                    self.agent.x, self.agent.y = nx, ny
                    self.set_cell(nx, ny, AGENT)
                    self.agent.steps += 1
                    return {"success": True, "message": "Used a key — door unlocked, you step through."}
                return {"success": False, "message": "Door is locked. Find a KEY first."}

            self.set_cell(ax, ay, EMPTY)
            self.agent.x, self.agent.y = nx, ny

            if target == KEY:
                self.agent.inventory.append(KEY)
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                return {"success": True, "message": f"Picked up KEY. Inventory: {self.agent.inventory}"}

            if target == CHEST:
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                self.done = True
                self.result = "success"
                self.agent.goal_achieved = True
                return {"success": True, "message": "GOAL REACHED — found the treasure chest!"}

            if target == EXIT:
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                self.done = True
                self.result = "success"
                self.agent.goal_achieved = True
                return {"success": True, "message": "GOAL REACHED — reached the exit!"}

            if target == HAZARD:
                self.agent.hazard_hits += 1
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                return {"success": True, "message": f"Stepped on hazard ({self.agent.hazard_hits} total). Keep going."}

            # Plain floor or open door
            self.set_cell(nx, ny, AGENT)
            self.agent.steps += 1
            return {"success": True, "message": f"Moved {direction}."}

        if action == "look":
            return {"success": True, "message": "You look around. Observation updated."}

        if action == "wait":
            self.agent.steps += 1
            return {"success": True, "message": "You wait."}

        return {"success": False, "message": f"Unknown action '{action}'."}

    def render(self):
        return "\n".join("".join(row) for row in self.grid)


# ── LLM helpers ──────────────────────────────────────────────

SERVER_URL = "http://localhost:5001/agent"

def call_server(messages):
    """POST conversation history to server.py, return the LLM reply string."""
    resp = requests.post(
        SERVER_URL,
        json={"messages": messages},
        timeout=90
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["content"]

def build_user_message(obs, last_result):
    parts = []
    if last_result:
        tag = "OK" if last_result["success"] else "FAIL"
        parts.append(f"[{tag}] {last_result['message']}")
    parts.append("Current observation:")
    parts.append(json.dumps(obs, indent=2))
    parts.append("Your next action (JSON only):")
    return "\n".join(parts)

def parse_action(raw):
    """Extract (action, params) from whatever the LLM returned."""
    text = raw.strip()
    # Strip markdown fences if present
    if "```" in text:
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.startswith("```"))
    # Find the first { ... } block
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        return "error", {"raw": raw}
    try:
        obj = json.loads(text[start:end])
        return obj.get("action", "error"), obj.get("params", {})
    except json.JSONDecodeError:
        return "error", {"raw": raw}


# ── Run loop ──────────────────────────────────────────────────

def run_agent(scenario_index=0, log_path=None, verbose=True):
    config = SCENARIOS[scenario_index]
    world  = World(config)

    run_log = {
        "scenario":   config.name,
        "goal":       config.goal,
        "model":      "llama3.1",
        "steps":      [],
        "result":     None,
    }

    conversation = []
    last_result  = None

    if verbose:
        print(f"\n{'='*55}")
        print(f"  {config.name}")
        print(f"  Goal: {config.goal}")
        print(f"{'='*55}")
        print(world.render())
        print()

    while not world.done and world.agent.steps < config.max_steps:
        obs      = world.observe()
        user_msg = build_user_message(obs, last_result)
        conversation.append({"role": "user", "content": user_msg})

        if verbose:
            print(f"Step {world.agent.steps + 1:>3}/{config.max_steps} | "
                  f"pos ({obs['position']['x']},{obs['position']['y']}) | "
                  f"inv {obs['inventory'] or '[]'}", end=" | ")

        # Call LLM via server.py
        try:
            raw_reply = call_server(conversation)
        except Exception as e:
            print(f"\nServer error: {e}")
            print("Is server.py running?  python server.py")
            sys.exit(1)

        conversation.append({"role": "assistant", "content": raw_reply})

        action, params = parse_action(raw_reply)
        if action == "error":
            result = {"success": False, "message": f"Could not parse reply: {raw_reply[:80]}"}
        else:
            result = world.act(action, params)

        last_result = result

        if verbose:
            tag = "OK  " if result["success"] else "FAIL"
            print(f"[{tag}] {action}({params}) -> {result['message'][:60]}")

        run_log["steps"].append({
            "step":      world.agent.steps,
            "position":  asdict(world.agent),
            "llm_reply": raw_reply,
            "action":    action,
            "params":    params,
            "result":    result,
        })

        # Small delay so Ollama isn't hammered continuously
        time.sleep(0.5)

    # Finish
    if world.agent.goal_achieved:
        world.result = "success"
        outcome = f"SUCCESS in {world.agent.steps} steps"
    else:
        world.result = "failure"
        outcome = f"FAILED (used all {config.max_steps} steps)"

    run_log["result"]      = world.result
    run_log["steps_taken"] = world.agent.steps
    run_log["hazard_hits"] = world.agent.hazard_hits

    if verbose:
        print(f"\n{outcome}")
        print(world.render())

    if log_path:
        with open(log_path, "w") as f:
            json.dump(run_log, f, indent=2)
        if verbose:
            print(f"Log saved -> {log_path}")

    return run_log


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LLM Agent World (Ollama)")
    parser.add_argument("--scenario",       type=int, default=0)
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--log",            type=str, default=None)
    parser.add_argument("--quiet",          action="store_true")
    args = parser.parse_args()

    if args.list_scenarios:
        for i, s in enumerate(SCENARIOS):
            print(f"[{i}] {s.name}: {s.description}")
        sys.exit(0)

    run_agent(
        scenario_index=args.scenario,
        log_path=args.log,
        verbose=not args.quiet,
    )

if __name__ == "__main__":
    main()