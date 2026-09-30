# SIH26123 — Edge-AI Based Distributed Fleet Coordination for AMRs
## Smart India Hackathon 2026 | Bharat Electronics Limited (BEL)

---

## What We Built
A **Python + Pygame 2D smart-warehouse simulator** with **3 Autonomous Mobile Robots (AMRs)**
that coordinate entirely through **peer-to-peer (P2P) communication** — no central controller.

---

## How to Run

```bash
# Install dependencies (one time)
pip install pygame matplotlib

# Run (from the parent folder)
python SIH26123/main.py

# Run a specific scenario directly (1-6)
python SIH26123/main.py 2
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `1` | Scenario 1 — Normal Operation |
| `2` | Scenario 2 — Narrow-Lane Conflict ⭐ |
| `3` | Scenario 3 — Starvation Test |
| `4` | Scenario 4 — Deadlock Pressure |
| `5` | Scenario 5 — Dynamic Obstacle |
| `6` | Scenario 6 — Control-Room Failure |
| `7` | Scenario 7 — Battery & Charging ⭐ |
| `O` | Toggle obstacle mode (then click grid) |
| `C` | Toggle control-room online/offline |
| `R` | Reset current scenario |
| `Q / Esc` | Quit + save results |

---

## File Structure

```
SIH26123/
├── main.py          ← Entry point, game loop
├── config.py        ← All tuneable parameters (weights, speed, etc.)
├── warehouse.py     ← Grid map, narrow lanes, obstacles
├── robot.py         ← Robot agent (state, A*, movement)
├── astar.py         ← A* path planning algorithm
├── communication.py ← Simulated P2P message bus
├── priority.py      ← Priority Score formula
├── conflict.py      ← Narrow-lane negotiation engine
├── scenarios.py     ← 6 demo scenarios
├── dashboard.py     ← Pygame visual dashboard
├── metrics.py       ← Performance metrics + CSV export
├── logger.py        ← Event logger
└── results/         ← Auto-generated CSVs and logs
```

---

## Core Algorithm: Priority Score

```
Score_i = α × Task_Priority + β × Urgency + γ × Wait_Factor

Wait_Factor = min(wait_seconds / 30, 5)   ← anti-starvation

Default weights:  α=0.5,  β=0.3,  γ=0.2
```

**Example:**
- R1: pri=5, urg=4, wait=0s  → Score = **3.70** → ENTERS lane
- R2: pri=4, urg=3, wait=10s → Score = **2.97** → WAITS
- After 30s wait: R2 score = **3.50** → R2 now gets priority

---

## What Each Scenario Demonstrates

| # | Scenario | Shows |
|---|----------|-------|
| 1 | Normal Operation | A*, movement, P2P, task cycling |
| 2 | Narrow-Lane Conflict | P2P negotiation, Priority Score, waiting |
| 3 | Starvation Test | Wait-time escalation, anti-starvation |
| 4 | Deadlock Pressure | 3-way negotiation, deterministic tie-break |
| 5 | Dynamic Obstacle | A* replanning at runtime |
| 6 | Control-Room Failure | Robots keep coordinating P2P without dashboard |

---

## Key Points for Judges

1. **No central controller** — the dashboard is visualization only
2. **Robots negotiate before entering** the narrow lane (pre-emptive, not reactive)
3. **Anti-starvation** — wait time always raises a robot's score
4. **Deterministic tie-breaking** — Robot ID (R1 < R2 < R3) prevents random decisions
5. **Metrics logged** — completion time, wait time, collisions, reroutes, messages

---

## Benchmark Comparison
Press `1` for our approach, note completion time.
Modify `config.py` → set `GAMMA = 0` to simulate stop-and-wait behavior for comparison.
