"""
Requires server.py running first.
"""

import sys
import json
import time
import argparse
from dataclasses import dataclass, field, asdict
from typing import Optional
import requests

# cell symbols
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
    KEY:    "key item",
    DOOR:   "locked door",
    OPEN:   "open door",
    CHEST:  "goal",
    HAZARD: "hazard",
    EXIT:   "exit",
}

DIRECTIONS = {
    "north": (0, -1),
    "south": (0,  1),
    "east":  (1,  0),
    "west":  (-1, 0),
}


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


# Scenarios

SCENARIOS = [
    # Task I — The Grain Room
    WorldConfig(
        name="Task I — The Grain Room",
        description="Collect an ant helper and reach the sorted grain pile.",
        grid=[
            "#########",
            "#@......#",
            "#.......#",
            "#...!...#",
            "#.......#",
            "####D####",
            "#...C...#",
            "#########",
        ],
        start=(1, 1),
        goal="Collect the ANT HELPER (K), pass through the GRAIN SACK (D), reach the SORTED PILE (C).",
        max_steps=35,
    ),

    # Task II — The Golden Fleece
    WorldConfig(
        name="Task II — The Golden Fleece",
        description="Collect wool from the brambles and reach the golden fleece.",
        grid=[
            "#########",
            "#@......#",
            "#.K.....#",
            "#.......#",
            "#..!!!..#",
            "#.......#",
            "#....C..#",
            "#########",
        ],
        start=(1, 1),
        goal="Collect WOOL FROM BRAMBLES (K), avoid the SUN-RAMS (!), reach the GOLDEN FLEECE (C).",
        max_steps=35,
    ),

    # Task III — The River Styx
    WorldConfig(
        name="Task III — The River Styx",
        description="Collect a river reed and reach the source of the Styx past the dragons.",
        grid=[
            "#########",
            "#@..K...#",
            "#.......#",
            "#.!.....#",
            "####D####",
            "#.......#",
            "#..!....#",
            "#...C...#",
            "#########",
        ],
        start=(1, 1),
        goal="Collect the CRYSTAL VESSEL (K), avoid the DRAGONS (!), meet the EAGLE (D), reach the SOURCE OF THE STYX (C).",
        max_steps=40,
    ),

    # Task IV — The Underworld
    WorldConfig(
        name="Task IV — The Underworld",
        description="Collect coins and honeycakes, pass through the Underworld gates, retrieve Persephone's box and exit.",
        grid=[
            "##########",
            "#@.K.....#",
            "#........#",
            "#...!....#",
            "#####D####",
            "#.K......#",
            "#........#",
            "#.....!..#",
            "#####D####",
            "#....C..E#",
            "##########",
        ],
        start=(1, 1),
        goal="Collect COINS AND CAKES (K), avoid PLEADING SOULS (!), pass through UNDERWORLD GATES (D), reach PERSEPHONE'S BOX (C), and return to the SURFACE (E).",
        max_steps=50,
    ),
]


# World Class

class World:
    def __init__(self, config):
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

        # passable directions
        passable = []
        blocked  = []
        adj      = {}
        for dirn, (dx, dy) in DIRECTIONS.items():
            ch = self.cell(ax + dx, ay + dy)
            can_pass = (
                ch not in (WALL, " ") and
                not (ch == DOOR and KEY not in self.agent.inventory)
            )
            adj[dirn] = {"symbol": ch, "name": ENTITY_NAMES.get(ch, "?"), "passable": can_pass}
            if can_pass:
                passable.append(dirn)
            else:
                blocked.append(dirn)

        # scan for nearby items
        nearby = []
        for iy in range(self.height):
            for ix in range(self.width):
                ch   = self.grid[iy][ix]
                dist = abs(ix - ax) + abs(iy - ay)
                if ch in (KEY, DOOR, CHEST, EXIT, HAZARD, OPEN) and dist <= 8:
                    rel_x = ix - ax
                    rel_y = iy - ay

                    candidates = []
                    if abs(rel_y) >= abs(rel_x):
                        if rel_y > 0:  candidates.append("south")
                        elif rel_y < 0: candidates.append("north")
                        if rel_x > 0:  candidates.append("east")
                        elif rel_x < 0: candidates.append("west")
                    else:
                        if rel_x > 0:  candidates.append("east")
                        elif rel_x < 0: candidates.append("west")
                        if rel_y > 0:  candidates.append("south")
                        elif rel_y < 0: candidates.append("north")

                    hint = next((d for d in candidates if d in passable), None) or (candidates[0] if candidates else None)

                    nearby.append({
                        "symbol":     ch,
                        "name":       ENTITY_NAMES.get(ch, "?"),
                        "relative_x": rel_x,
                        "relative_y": rel_y,
                        "distance":   dist,
                        "move_hint":  hint,
                    })

        nearby.sort(key=lambda i: i["distance"])

        return {
            "position":            {"x": ax, "y": ay},
            "inventory":           list(self.agent.inventory),
            "steps_remaining":     self.config.max_steps - self.agent.steps,
            "goal":                self.config.goal,
            "passable_directions": passable,
            "blocked_directions":  blocked,
            "adjacent_cells":      adj,
            "nearby_items":        nearby[:6],
            "hazard_hits":         self.agent.hazard_hits,
        }

    def act(self, action, params):
        ax, ay = self.agent.x, self.agent.y

        if action == "move":
            direction = params.get("direction", "").strip().lower()
            if direction not in DIRECTIONS:
                return {"success": False, "message": f"Unknown direction '{direction}'."}
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
                    return {"success": True, "message": "Used key — door opened."}
                return {"success": False, "message": "Door is locked. Find a key first."}

            self.set_cell(ax, ay, EMPTY)
            self.agent.x, self.agent.y = nx, ny

            if target == KEY:
                self.agent.inventory.append(KEY)
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                return {"success": True, "message": f"Picked up key. Inventory: {self.agent.inventory}"}

            if target == CHEST:
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                self.done   = True
                self.result = "success"
                self.agent.goal_achieved = True
                return {"success": True, "message": "TASK COMPLETE!"}

            if target == EXIT:
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                self.done   = True
                self.result = "success"
                self.agent.goal_achieved = True
                return {"success": True, "message": "TASK COMPLETE — returned safely!"}

            if target == HAZARD:
                self.agent.hazard_hits += 1
                self.set_cell(nx, ny, AGENT)
                self.agent.steps += 1
                return {"success": True, "message": f"Hit a hazard ({self.agent.hazard_hits} total)."}

            self.set_cell(nx, ny, AGENT)
            self.agent.steps += 1
            return {"success": True, "message": f"Moved {direction}."}

        if action == "look":
            return {"success": True, "message": "Looking around."}

        if action == "wait":
            self.agent.steps += 1
            return {"success": True, "message": "Waited."}

        return {"success": False, "message": f"Unknown action '{action}'."}

    def render(self):
        return "\n".join("".join(row) for row in self.grid)


# call LLM

def call_server(messages):
    resp = requests.post(
        "http://localhost:5001/agent",
        json={"messages": messages},
        timeout=120
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
    parts.append("Observation:\n" + json.dumps(obs, indent=2))
    parts.append("Your action:")
    return "\n".join(parts)

def parse_action(raw):
    txt = raw.replace("```", "").strip()
    a = txt.find("{")
    b = txt.rfind("}") + 1
    if a == -1 or b == 0:
        return "error", {"raw": raw}
    try:
        obj = json.loads(txt[a:b])
        return obj.get("action", "error"), obj.get("params", {})
    except:
        return "error", {"raw": raw}


# Run Loop

def run_agent(scenario_index=0, log_path=None, verbose=True):
    config = SCENARIOS[scenario_index]
    world  = World(config)

    run_log = {
        "scenario": config.name,
        "goal":     config.goal,
        "model":    "qwen2.5:0.5b",
        "steps":    [],
        "result":   None,
    }

    conversation = []
    last_result  = None
    move_history = [] 

    if verbose:
        print(f"\n{'='*50}")
        print(f"  {config.name}")
        print(f"  {config.goal}")
        print(f"{'='*50}")
        print(world.render())
        print()

    while not world.done and world.agent.steps < config.max_steps:
        obs = world.observe()

        user_msg = build_user_message(obs, last_result)
        conversation.append({"role": "user", "content": user_msg})

        if verbose:
            print(f"Step {world.agent.steps+1:>2}/{config.max_steps} | "
                  f"pos ({obs['position']['x']},{obs['position']['y']}) | "
                  f"inv {obs['inventory'] or '[]'} | "
                  f"passable {obs['passable_directions']}", end=" ")

        try:
            raw = call_server(conversation)
        except Exception as e:
            print(f"\nServer error: {e}\nIs server.py running?")
            sys.exit(1)

        conversation.append({"role": "assistant", "content": raw})
        action, params = parse_action(raw)

        # override bad moves
        override = None
        if action == "move" and "direction" in params:
            chosen = params["direction"]

            is_looping = (
                len(move_history) >= 4 and
                len(set(move_history[-4:])) <= 2
            )

            if is_looping:
                recent  = set(move_history[-4:])
                fresh   = next((d for d in obs["passable_directions"] if d not in recent), None)
                if fresh:
                    params["direction"] = fresh
                    override = f"loop -> {fresh}"
            elif chosen in obs["blocked_directions"]:
                target = next(
                    (i for i in obs["nearby_items"] if i["symbol"] in ("K","C","E","D") and i.get("move_hint")),
                    None
                )
                if target:
                    params["direction"] = target["move_hint"]
                    override = f"wall -> {params['direction']}"
                elif obs["passable_directions"]:
                    params["direction"] = obs["passable_directions"][0]
                    override = f"wall -> {params['direction']}"

            move_history.append(params["direction"])
            if len(move_history) > 6:
                move_history.pop(0)

        if action == "error":
            result = {"success": False, "message": f"Could not parse: {raw[:60]}"}
        else:
            result = world.act(action, params)

        last_result = result

        if verbose:
            tag = "OK  " if result["success"] else "FAIL"
            over = f" [{override}]" if override else ""
            print(f"| [{tag}]{over} {result['message'][:50]}")

        run_log["steps"].append({
            "step":     world.agent.steps,
            "position": asdict(world.agent),
            "llm_raw":  raw,
            "action":   action,
            "params":   params,
            "override": override,
            "result":   result,
        })

        time.sleep(0.3)

    if world.agent.goal_achieved:
        world.result = "success"
        msg = f"\nSUCCESS in {world.agent.steps} steps."
    else:
        world.result = "failure"
        msg = f"\nFAILED after {config.max_steps} steps."

    run_log["result"]      = world.result
    run_log["steps_taken"] = world.agent.steps
    run_log["hazard_hits"] = world.agent.hazard_hits

    if verbose:
        print(msg)
        print(world.render())

    if log_path:
        with open(log_path, "w") as f:
            json.dump(run_log, f, indent=2)
        if verbose:
            print(f"Log saved: {log_path}")

    return run_log


# Main

def main():
    parser = argparse.ArgumentParser()
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