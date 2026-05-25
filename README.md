# Psyche & Cupid — LLM Agent in a Virtual World

An LLM-powered autonomous agent navigating the four trials of Psyche, based on Apuleius, 'The Golden Ass', Books IV–VI, c.160 AD. I decided to use this theme
for the Virtual World because I most recently finished reading 'Till we have faces' by C.S. Lewis and I thought the trials made for synonymous agent challenges.

The agent (Psyche) perceives her environment, reasons using a local LLM, and takes actions to complete each mythological task.

## Literary Source

**Apuleius, Metamorphoses (The Golden Ass), Books IV–VI, c.160 AD**

The Latin novel detailing the Eros and Psyche myth. Psyche, a mortal, provokes the jealousy of Aphrodite (Venus), who sets her four seemingly impossible tasks.
With help from unexpected allies (ants, a reed, an eagle, a speaking tower) Psyche completes each one. Eros (Cupid) intervenes with Zeus, who grants Psyche
immortality.

---

## The Four Tasks

### Task I — The Grain Room
Aphrodite empties a vast storehouse of mixed grain (wheat, barley, millet,
lentils, beans) and orders Psyche to sort every grain into separate piles
by nightfall. An army of ants takes pity on her and does the work.

**Mechanics:**
- 'K' Ant helpers — collect them to assist the sort
- 'D' Grain sacks — deposits for sorted grain, opened with an ant helper
- 'C' Sorted pile — the completed task, your goal

---

### Task II — The Golden Fleece
Psyche must gather golden wool from a flock of violent sun-rams that will
trample anyone who approaches. A river reed whispers to her to wait until
midday when the rams sleep, then collect wool caught on the brambles.

**Mechanics:**
- 'K' Wool on brambles — collect from the meadow edge
- '!' Sun-rams — patrol the central meadow, avoid them
- 'C' Golden fleece — the accumulated wool, your goal

---

### Task III — The River Styx
Psyche must fill a crystal flask at the source of the river Styx, which
flows from a sheer cliff guarded by sleepless dragons. Zeus's eagle pities
her and fetches the water, but in the game Psyche must navigate herself.

**Mechanics:**
- 'K' Crystal Vessel — to contain the water
- '!' Sleepless dragons — patrol each level of the cliff
- 'D' Cliff gates — sealed rock passages, opened with the flask
- 'C' Source of the Styx — fill the crystal flask here

---

### Task IV — The Underworld
The most difficult task. Psyche must descend to Hades, collect Persephone's
box, and return. A speaking tower gives her precise instructions:
bring coins for Charon, honeycakes for Cerberus, ignore all souls who beg for help,
and above all "do not open the box".

**Mechanics:**
- 'K' Coins and honeycakes — needed to pay Charon and appease Cerberus
- '!' Pleading souls — the desperate dead who will slow you, ignore them
- 'D' Underworld gates — Charon's ferry and Cerberus's post, opened with coins/cakes
- 'C' Persephone's box — your goal (do not open it)
- 'E' Exit — the return to the surface

---

## Setup

### Requirements
```bash
pip install flask flask-cors requests
```

Ollama must be installed: https://ollama.com

### Recommended model
```bash
ollama pull qwen2.5:0.5b
```

### Start order — two terminals

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
python PsycheServer.py
```
You should see `Ollama: RUNNING` and the model listed as ready.

**Open html in browser:**
Open 'simpleBrowserUI' in your browser from Finder.

---

## Files

| File | Purpose |
|---|---|
| 'PsycheServer.py' | Flask server — receives requests, adds system prompt, calls Ollama |
| 'simpleAgentWorld.py' | Terminal runner — world physics, scenarios, perceive/reason/act loop |
| 'simpleBrowserUI.html' | Browser UI — canvas display, event log, per-task colour schemes |
| 'README.md' | This file |
| 'example_run_log.json' | Sample log of a Task I run |
