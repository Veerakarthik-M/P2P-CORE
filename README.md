# P2P-CORE — Decentralized AMR Fleet Coordination
### SIH 2026 | Problem Statement 26123

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![SIH](https://img.shields.io/badge/SIH%202026-Problem%2026123-orange)

</div>

---

## What This Is

A working Python + Pygame simulation of **3 Autonomous Mobile Robots (AMRs)** coordinating in a smart warehouse — **without any central server**.

Each robot:
- Plans its own path using **A\*** locally
- Broadcasts its state directly to other robots every second (**simulated P2P**)
- Negotiates narrow-lane access using a **priority score formula**
- Handles its own **battery management and charging**
- Makes every movement decision independently

The monitoring dashboard shows what is happening — it does **not** control the robots. Robots keep operating correctly even when the dashboard goes offline.

> ⚠️ **Honest scope:** Communication is simulated in-process (not real Wi-Fi). This is a software prototype, not a physical deployment.

---

## The Problem

Modern warehouse fleets rely on a **centralized server** for all path planning decisions. Every robot asks the server where to go, waits for a reply, then moves. This creates three real problems:

| Problem | What happens |
|---------|--------------|
| **Network latency** | Every decision needs a server round-trip — robots slow down |
| **Wi-Fi dead zones** | Robot loses signal → loses direction → stops |
| **Single point of failure** | Server goes down → entire fleet halts |

Our solution removes the central server entirely. Decision-making moves to each robot individually — edge computing, at the device.

---

## How the Simulation Works

The simulation runs at **10 FPS** on a **22 × 28 cell grid** warehouse map.

### Every tick (100ms)
1. `ConflictManager.resolve()` scans all robots' next 5 path cells for narrow-lane collisions
2. Each robot's `step()` is called — moves one cell if path is clear
3. Battery drains based on movement state
4. If a robot has been blocked for **> 2.5s**, the Binary Assignment Deadlock Resolver fires
5. Dashboard renders updated state

### Every second
- Each robot **broadcasts** a 9-field state message to all others
- Robots read peer messages to anticipate each other's movements

### On task completion
- Robot picks the next task from the shared task pool
- A\* immediately plans a new path

---

## Codebase — Files and Responsibilities

Every claim in this README is verified against the actual source files below.

| File | Lines | What it does |
|------|-------|--------------|
| `main.py` | 556 | Game loop, scenario switching, battery/charging orchestration, deadlock resolver |
| `robot.py` | 372 | Robot class — state machine, A\* calls, battery drain, charging, event log |
| `astar.py` | 79 | Pure A\* function — Manhattan heuristic, min-heap, returns path as list of cells |
| `warehouse.py` | 140 | 22×28 grid map, narrow-lane registry, charging-station registry, dynamic obstacles |
| `conflict.py` | 220 | ConflictManager — narrow-lane detection, NEGOTIATE/GRANT/YIELD negotiation |
| `priority.py` | 44 | `priority_score()` formula, `choose_lane_owner()` tie-breaking |
| `communication.py` | 129 | MessageBus — `broadcast()`, `log_negotiation()`, `get_negotiation_log()` |
| `dashboard.py` | 614 | 5-tab Pygame UI — battery bars, STALLED detection, conflict log |
| `scenarios.py` | 196 | 7 scenario factory functions (press keys 1–7) |
| `metrics.py` | 108 | MetricsTracker — collisions, reroutes, wait time, messages, CSV export |
| `logger.py` | 37 | SimLogger — saves conflict/reroute/task events to `results/sim_log_*.txt` |
| `config.py` | 65 | All constants — grid size, FPS, battery params, priority weights, colors |

---

## Feature Status

| Feature | Status | Where in code |
|---------|--------|---------------|
| 3 AMRs (R1, R2, R3) | ✅ Implemented | `robot.py`, `scenarios.py` |
| Local A\* path planning | ✅ Implemented | `astar.py`, `robot.plan_path()` |
| Dynamic replanning on obstacle | ✅ Implemented | `robot.replan()`, `main.py` |
| Simulated P2P communication | ✅ Implemented | `communication.py` MessageBus |
| State broadcast every 1 second | ✅ Implemented | `main.py` MSG_INTERVAL |
| Narrow-lane conflict detection | ✅ Implemented | `conflict.py` ConflictManager |
| NEGOTIATE → GRANT → YIELD | ✅ Implemented | `conflict.py`, `communication.py` |
| Priority score formula | ✅ Implemented | `priority.py priority_score()` |
| Anti-starvation (wait-time boost) | ✅ Implemented | `priority.py wait_factor()` |
| Binary assignment deadlock resolver | ✅ Implemented | `main.py _resolve_cell_deadlocks()` |
| Dynamic obstacle (mouse click) | ✅ Implemented | `warehouse.toggle_obstacle()` |
| Control-room offline simulation | ✅ Implemented | `main.py` key `C`, scenario 6 |
| 5-tab Pygame dashboard | ✅ Implemented | `dashboard.py` |
| Battery drain (LOW / CRITICAL) | ✅ Implemented | `robot.update_battery()` |
| Auto-navigate to charger | ✅ Implemented | `robot.navigate_to_charger()` |
| Charge at station + resume task | ✅ Implemented | `robot.tick_charging()`, `resume_after_charging()` |
| STALLED display detection | ✅ Implemented | `robot.display_state` property |
| Task cycling after completion | ✅ Implemented | `main.py _assign_next_task()` |
| Metrics + CSV export | ✅ Implemented | `metrics.py save_csv()` |
| Collision prevention (cell check) | ✅ Implemented | `robot.step()` |
| Real Wi-Fi / network communication | ❌ Not implemented — simulation only | — |
| Raspberry Pi / Jetson deployment | ❌ Not implemented — future | — |
| Task reassignment on robot failure | ⚠️ Partial — task returns to pool, no explicit failure state | `main.py` |
| 20% improvement measured | ⚠️ Not measured — baseline field exists but is never populated | `metrics.baseline_time` |

---

## The 3 Robots

### R1 — Teal-Green

| Property | Value |
|----------|-------|
| Start position | Row 1, Col 1 (top-left) |
| Task priority | 5 (highest) |
| Urgency | 4 |
| Initial battery | 92% |
| Score at t=0 | 0.5×5 + 0.3×4 = **3.70** |

In **Scenario 2**: starts at (5,1), target (1,26) — must cross narrow lane at (6,9). Wins the negotiation against R2.

### R2 — Purple

| Property | Value |
|----------|-------|
| Start position | Row 1, Col 26 (top-right) |
| Task priority | 4 |
| Urgency | 3 |
| Initial battery | 78% |
| Score at t=0 | 0.5×4 + 0.3×3 = **2.90** |

In **Scenario 2**: starts at (7,1), same narrow lane target — loses negotiation to R1, sends YIELD.

### R3 — Amber

| Property | Value |
|----------|-------|
| Start position | Row 20, Col 1 (bottom-left) |
| Task priority | 3 (lowest) |
| Urgency | 2 |
| Initial battery | 65% |
| Score at t=0 | 0.5×3 + 0.3×2 = **2.10** |

In **Scenario 3**: pre-loaded with `wait_time = 25.0s` — score already boosted, rises further as it waits.  
In **Scenario 7**: starts at 12% battery (CRITICAL) — immediately navigates to C1, charges to 80%, resumes task.

---

## P2P Communication

### Is it real?

**No — it is simulated in-process.** The `MessageBus` in `communication.py` is an in-memory Python object. There is no real Wi-Fi, no network socket, no Bluetooth. On real hardware, this would be replaced by ZeroMQ, MQTT, or ROS2 without changing any robot logic.

### Architecture

```
R1.broadcast() ──┐
R2.broadcast() ──┤──► MessageBus (in-memory) ◄── R1.get_messages()
R3.broadcast() ──┘                                R2.get_messages()
                                                  R3.get_messages()
```

The `MessageBus` is **not a decision-maker**. It only stores and forwards. No central authority.

### State Message Schema (every 1 second)

```python
{
  "robot_id"      : "R1",
  "position"      : [5, 1],
  "target"        : [1, 26],
  "task_priority" : 5,
  "urgency"       : 4,
  "wait_time"     : 0.0,
  "ETA"           : 4.5,
  "sim_time"      : 12.0,
  "state"         : "MOVING",
  "next_cells"    : [[5,2],[5,3],[5,4]],
  "battery"       : 91.4
}
```

### Directed Negotiation Messages

| Type | Direction | Meaning |
|------|-----------|---------|
| `NEGOTIATE` | R1 → R2 | "I intend to enter Lane #0. My score: 3.70" |
| `GRANT` | R1 → R2 | "Lane #0 is mine. I proceed." |
| `YIELD` | R2 → R1 | "Acknowledged. I am waiting." |
| `PRIORITY` | R1 → R2 | "Binary assign: I=1, you=0. Clear my path." |
| `DETECT` | R2 → R1 | "You are blocking my path." |
| `REROUTE` | Rx → ALL | "Obstacle detected. Replanning." |
| `BATT_LOW` | Rx → ALL | "Battery CRITICAL. Heading to charger." |
| `CHARGING` | Rx → ALL | "Docked at C1. Charging." |
| `CHARGED` | Rx → ALL | "Charged to 80%. Resuming task." |
| `CTRL_ROOM` | SYS → ALL | "Control Room is now OFFLINE." |

### Example — Full Narrow-Lane Negotiation Sequence

```
[10.0s] R1 → ALL  : pos=[5,1] state=MOVING           (heartbeat)
[10.0s] R2 → ALL  : pos=[7,1] state=MOVING           (heartbeat)
[10.5s] R1 → R2   [NEGOTIATE] entering Lane #0. score=3.70
[10.5s] R2 → R1   [NEGOTIATE] entering Lane #0. score=2.90
[10.5s] R1 → R2   [GRANT]     Lane #0 GRANTED to me.
[10.5s] R2 → R1   [YIELD]     Acknowledged. Waiting.
```

R1 → ENTERING_LANE → IN_LANE.  
R2 → WAITING (orange ring on map).  
When R1 exits the narrow cell → lane released → R2 → MOVING automatically.

---

## Path Planning

**Algorithm:** A\* with Manhattan distance heuristic  
**File:** `astar.py` — 79 lines, pure function, no side effects  
**Movement:** 4-directional (up, down, left, right) — no diagonal

### Input / Output

```
astar(grid, start, goal, reserved_cells)
→ list of (row, col) tuples from start to goal
→ empty list if no path exists
```

| Input | Type | Description |
|-------|------|-------------|
| `grid` | 2D list | 0=blocked, 1=walkable — from `warehouse.get_grid_for_astar()` |
| `start` | (row, col) | Robot's current position |
| `goal` | (row, col) | Delivery target |
| `reserved_cells` | set | Other robots' positions — treated as blocked for this call |

### When path is recalculated

| Trigger | What calls it |
|---------|---------------|
| New task assigned | `robot.assign_task()` → `plan_path()` |
| Next cell blocked by robot or obstacle | `robot.replan()` |
| Deadlock resolver backs robot up | `robot.replan()` from backup cell |
| Charging complete | `resume_after_charging()` → `plan_path()` to saved task target |

Path is **not** continuously recalculated every tick. It replans **reactively** — only when the current path becomes invalid.

---

## Conflict Resolution

Two separate mechanisms handle two different situations.

### Mechanism A — Narrow-Lane Negotiation (conflict.py)

Fires **before** robots enter the lane — pre-emptive.

1. `ConflictManager.resolve()` runs every tick
2. Looks at each robot's **next 5 cells** in its planned path
3. If 2+ robots' paths share the same narrow-lane cell → conflict detected
4. Scores compared → GRANT to winner → YIELD from losers
5. Winner: ENTERING_LANE state — proceeds
6. Losers: WAITING state — wait_time accumulates

There are **4 narrow lanes** in the warehouse:

| Lane ID | Cell | Location |
|---------|------|----------|
| 0 | (6, 9) | Top-center choke point |
| 1 | (6, 21) | Top-right choke point |
| 2 | (12, 9) | Mid-center choke point |
| 3 | (12, 21) | Mid-right choke point |

### Mechanism B — Cell-Level Deadlock Resolver (main.py)

Fires **after** a robot has been WAITING for **> 2.5 seconds** — reactive.

Works like a binary constraint (MILP-style):
```
x(winner) = 1  →  proceeds forward
y(loser)  = 0  →  physically moved to backup cell, replans
x + y = 1      →  exactly one robot gets access
```

**Special rule:** IDLE robots with no active task always lose — score is forced to 0.0. Any active robot beats an idle one regardless of priority values.

### Priority Score Formula

```
Score = 0.5 × TaskPriority  +  0.3 × Urgency  +  0.2 × WaitFactor

WaitFactor = min(wait_seconds / 30.0, 5.0)    ← saturates at 5
```

**Constants from config.py:**  `ALPHA = 0.5`, `BETA = 0.3`, `GAMMA = 0.2`

**Tie-break:** If scores are equal, smaller robot_id wins: R1 < R2 < R3

### Worked Example — Scenario 2 at t=0

| Robot | P | U | wait_seconds | W | Score |
|-------|---|---|-------------|---|-------|
| R1 | 5 | 4 | 0.0 | 0.0 | 0.5×5 + 0.3×4 + 0.2×0 = **3.70** |
| R2 | 4 | 3 | 0.0 | 0.0 | 0.5×4 + 0.3×3 + 0.2×0 = **2.90** |

R1 wins. R1 → GRANT. R2 → YIELD → WAITING.

---

## Anti-Starvation

A robot that keeps losing builds up `wait_time`. The `WaitFactor` grows as:

```
WaitFactor = min(wait_seconds / 30.0, 5.0)
```

After 30 seconds of waiting, WaitFactor = 5.0, adding **+1.0** to a robot's score. A previously-losing robot eventually scores higher than the robot that kept winning. The system is self-balancing — no robot is permanently blocked.

**Scenario 3** demonstrates this: R3 starts with `wait_time = 25.0s` pre-loaded. Its score is already boosted. As it waits in live negotiation, the score rises further on screen until R3 wins access.

---

## Battery & Charging

### Drain rates (from config.py)

| State | Drain per second |
|-------|-----------------|
| MOVING | 1.5% |
| IDLE / WAITING | 0.1% |
| CHARGING | 0% (no drain) |

### Thresholds

| Level | Battery % | What happens |
|-------|-----------|--------------|
| NORMAL | ≥ 30% | Green bar |
| LOW | 15–29% | Orange bar, `(LOW)` label |
| CRITICAL | < 15% | Red bar, robot navigates to nearest charger |

### Charging cycle

1. Battery drops below 15% → CRITICAL
2. Robot broadcasts `BATT_LOW` to fleet
3. Saves current task target (`_pre_charge_target`)
4. Navigates to nearest **free** charging station
5. Docks → state = `CHARGING`, yellow ring on map
6. Charges at **5%/sec** until battery ≥ 80%
7. Broadcasts `CHARGED` to fleet
8. Calls `resume_after_charging()` → replans path back to saved task

### Charging Stations

| Station | Grid position | Area |
|---------|--------------|------|
| C1 | Row 1, Col 3 | Top-left |
| C2 | Row 20, Col 24 | Bottom-right |

If C1 is occupied, robot routes to C2 automatically.

---

## Dynamic Obstacle Handling

Press `O` to enter obstacle mode, then click any floor cell. The cell turns red.

What happens internally:
1. `warehouse.toggle_obstacle(r, c)` — cell added to `dynamic_obstacles` set
2. `get_grid_for_astar()` returns the cell as 0 (blocked)
3. All robots with an active task immediately call `robot.replan()`
4. A\* reruns on the updated grid — new route around the obstacle
5. Reroutes counter increments in the dashboard
6. Click again to remove — robots may replan through it again

This is **different from robot-robot conflict**:

| | Dynamic Obstacle | Robot-Robot Conflict |
|--|--|--|
| What is blocked | Floor cell permanently marked | Another robot's current cell |
| Detection | A\* grid = 0 | `if next_cell in other_positions` |
| Who replans | All robots with a target | Only the blocked robot |
| Duration | Until user removes it | Temporary — robot moves away |

**Scenario 5** pre-places obstacles at cells (5,13) and (5,14) on load.

---

## Dashboard

The dashboard **reads** robot state only. It sends zero commands to robots.

### What's on screen

```
┌─────────────────────────────────────────────────────────────────────┐
│  Left side (22×28 grid)          │  Right side (410px dashboard)   │
│                                  │                                  │
│  Dark cells = racks (blocked)    │  Header: SMART WAREHOUSE SIH26123│
│  Light cells = floor (walkable)  │  Scenario name + pause status    │
│  Blue N cells = narrow lanes     │  CTRL ROOM: ONLINE / OFFLINE     │
│  Yellow cells = charging station │  ─────────────────────────────── │
│  Red cells = dynamic obstacles   │  Tab bar: FLEET R1 R2 R3 CONFLICT│
│  Magenta cells = robot targets   │                                  │
│                                  │  [tab content below]             │
│  Robots = filled circles         │                                  │
│  Ring color = current state      │                                  │
│  Badge above = priority score    │                                  │
│  Dim trail = planned A* path     │                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Robot ring colors

| Color | State |
|-------|-------|
| Green | MOVING |
| Orange | WAITING |
| Light blue | ENTERING_LANE / IN_LANE |
| Yellow | CHARGING |
| Bright red | STALLED (position unchanged for > 4s while MOVING) |

---

### Tab: FLEET `[F1]`

- Battery bar per robot (green/orange/red) + % label + status tag
- Current state, position, priority score, wait time for each robot
- Latest narrow-lane conflict result (lane ID, winner, loser, scores)
- P2P communication log — last 10 messages, color-coded by type
- Charging station status (AVAILABLE / OCCUPIED — robotID)
- Fleet metrics: sim time, tasks, collisions, reroutes, total wait, messages

### Tabs: R1 / R2 / R3 `[F2 / F3 / F4]`

- Current state + position + target + ETA
- Priority score breakdown: live P, U, W values with formula
- Battery bar + NORMAL / LOW / CRITICAL label
- Path progress: Step X/Y (Z%)
- Decision log: last 8 timestamped events for this robot

### Tab: CONFLICT `[F5]`

- P2P Negotiation Log (always at top) — last 8 messages, color-coded
- Latest lane negotiation: lane #, timestamp, each robot's score, result
- Lane conflict history: last 4 events

#### Negotiation log message colors

| Color | Message types |
|-------|--------------|
| Green | `[GRANT]`, `[PRIORITY]` |
| Red | `[YIELD]`, `[DETECT]`, `[REROUTE]` |
| Yellow | `[BATT_LOW]`, `[CHARGING]` |
| Cyan | `[CHARGED]` |
| Blue | `[NEGOTIATE]`, state broadcasts |

---

## Demo Scenarios (Press 1–7)

| Key | Scenario | What it demonstrates |
|-----|----------|----------------------|
| `1` | Normal Operation | All 3 robots navigate independently using local A\* |
| `2` | Narrow-Lane Conflict ⭐ | R1 vs R2 at choke point — full NEGOTIATE→GRANT→YIELD sequence live |
| `3` | Starvation Test | R3 (low priority, 25s wait preloaded) score rises live until R3 wins |
| `4` | Deadlock Pressure | All 3 robots converge on same area — binary assignment fires |
| `5` | Dynamic Obstacle | Pre-placed obstacles — A\* replans immediately |
| `6` | Control-Room Failure | Press C → OFFLINE — robots keep coordinating without monitoring |
| `7` | Battery & Charging | R3 at 12% → routes to C1 → docks → charges → resumes task |

### What each robot does per scenario

**Scenario 1 — Normal**
- R1: (1,1) → (20,26)
- R2: (1,26) → (20,1)
- R3: (20,1) → (1,26)

**Scenario 2 — Narrow-Lane Conflict**
- R1: (5,1) → (1,26) — crosses lane at (6,9) — wins negotiation
- R2: (7,1) → (1,25) — crosses same lane — yields to R1
- R3: (17,1) → (1,7) — separate path

**Scenario 3 — Starvation Test**
- R1: (5,1) → (1,26) — priority 5, urgency 5
- R2: (7,1) → (1,25) — priority 5, urgency 4
- R3: (11,1) → (1,20) — priority 2, urgency 1 — `wait_time = 25.0s` pre-loaded

**Scenario 4 — Deadlock Pressure**
- All 3 robots approach the same bottleneck simultaneously — binary resolver fires

**Scenario 5 — Dynamic Obstacle**
- Normal start positions + obstacles pre-placed at (5,13) and (5,14)

**Scenario 6 — Control-Room Failure**
- Normal start positions — simulation begins with CTRL ROOM: OFFLINE

**Scenario 7 — Battery & Charging**
- R1: battery=85%, target (20,26)
- R2: battery=55%, target (20,1)
- R3: battery=12% (CRITICAL), target (1,26) — immediately routes to C1

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `1`–`7` | Load scenario |
| `SPACE` | Pause / Resume |
| `R` | Reset current scenario |
| `O` + click | Place / remove dynamic obstacle on grid |
| `C` | Toggle control room online / offline |
| `TAB` | Cycle dashboard tabs |
| `F1` | FLEET tab |
| `F2` | R1 tab |
| `F3` | R2 tab |
| `F4` | R3 tab |
| `F5` | CONFLICT tab |
| `Q` / `ESC` | Quit — saves `results/simulation_results.csv` |

---

## System Architecture

```
                    ┌──────────────────────────────────┐
                    │         warehouse.py              │
                    │  22×28 Grid  |  4 Narrow Lanes   │
                    │  2 Chargers  |  Dynamic Obstacles │
                    └───────────────┬──────────────────┘
                                    │ shared read-only map
          ┌─────────────────────────┼────────────────────────┐
          │                         │                        │
     ┌────┴────┐               ┌────┴────┐              ┌────┴────┐
     │   R1    │               │   R2    │              │   R3    │
     │  astar  │◄─────────────►│  astar  │◄────────────►│  astar  │
     │  Local  │   P2P via     │  Local  │  P2P via    │  Local  │
     │  State  │  MessageBus   │  State  │  MessageBus │  State  │
     └────┬────┘               └────┬────┘              └────┬────┘
          │                         │                        │
          └─────────────────────────┼────────────────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │     ConflictManager (per tick)    │
                    │   Narrow-lane pre-emptive nego.   │
                    └───────────────┬──────────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │  _resolve_cell_deadlocks() main.py│
                    │  Binary Assignment (x+y=1)        │
                    └───────────────┬──────────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │    dashboard.py (monitor only)    │
                    │  5-Tab Pygame UI — reads state    │
                    │  Sends ZERO commands to robots    │
                    └──────────────────────────────────┘
```

**Passive shared components:** `MessageBus` (stores/forwards only), `ConflictManager` (evaluates only)  
**Active, independent:** Each `Robot` object makes all its own decisions

---

## Installation & Run

**Requirement:** Python 3.11+ and Pygame

```bash
pip install pygame
```

```bash
git clone https://github.com/Veerakarthik-M/P2P-CORE.git
cd P2P-CORE
python SIH26123/main.py
```

**Health check (verify all modules load correctly):**
```bash
python health_check.py
```

---

## Tech Stack

| Tool | Role |
|------|------|
| Python 3.11+ | Language — clean OOP, no compilation needed |
| Pygame | 2D simulation window, rendering, keyboard/mouse input, 10 FPS loop |
| heapq (stdlib) | Priority queue for A\* open set |
| csv (stdlib) | Metrics export to `results/simulation_results.csv` |
| json (stdlib) | Message structure serialization |

**Why Python + Pygame?**  
Python makes the algorithm readable and verifiable. A\* on a 22×28 grid runs in under 1ms — suitable for Raspberry Pi 4. The same robot agent architecture would deploy as a standalone process on each physical robot.

---

## Results

Across all 7 scenarios tested in this prototype:

| Metric | Result |
|--------|--------|
| Inter-robot collisions | **0** in all scenarios |
| Narrow-lane negotiations | Resolved automatically via GRANT/YIELD |
| Starvation cases | Handled — WaitFactor raises score over time |
| Dynamic obstacle replanning | Instant — robots reroute within 1 tick |
| Control-room-offline operation | Robots unaffected — continue coordinating |
| Battery auto-charging | Working — dock → charge → resume saved task |
| CSV metrics export | Auto-saved on quit |

> **20% improvement target:** The `MetricsTracker` has a `baseline_time` field built in for stop-and-wait comparison. In the current prototype this field is not yet populated across systematic runs. Formal benchmarking is a planned next step.

---

## Project Structure

```
P2P-CORE/
├── SIH26123/
│   ├── main.py           # Entry point, game loop, orchestration
│   ├── robot.py          # Robot agent class
│   ├── astar.py          # A* path planner
│   ├── warehouse.py      # Grid map + narrow lanes + chargers
│   ├── conflict.py       # ConflictManager — lane negotiation
│   ├── priority.py       # Priority score formula
│   ├── communication.py  # MessageBus — P2P simulation
│   ├── dashboard.py      # 5-tab Pygame UI
│   ├── scenarios.py      # 7 demo scenarios
│   ├── metrics.py        # MetricsTracker + CSV export
│   ├── logger.py         # SimLogger — text event log
│   └── config.py         # All constants
├── health_check.py       # Module import + sanity tests
├── results/              # Auto-generated: CSV + log files
└── README.md
```

---

## What Is Implemented vs What Is Future

### Currently working in this prototype
- 3 independent robot agents with local A\* path planning
- Simulated P2P state broadcasts every 1 second (9-field message)
- 10 directed negotiation message types
- Narrow-lane pre-emptive conflict resolution (4 choke points)
- Priority score formula with live anti-starvation WaitFactor
- Cell-level binary assignment deadlock resolver (2.5s threshold)
- Dynamic obstacle placement + immediate A\* replanning
- Control-room offline simulation (edge independence demonstrated)
- Battery drain, LOW/CRITICAL thresholds, auto charger routing
- Full charging cycle: navigate → dock → charge → resume
- 5-tab dashboard with battery bars, STALLED detection, P2P log
- Metrics collection and CSV export on quit
- 7 scenarios covering all key SIH26123 requirements
- Text simulation log saved to results/

### Planned future extensions
- Real P2P network communication (ZeroMQ / MQTT / ROS2)
- Edge hardware deployment (Raspberry Pi 4 / Jetson Nano)
- Systematic baseline comparison (20% improvement measurement)
- Full robot failure handling with task handoff
- Zone-based conflict management for larger fleets (> 3 robots)
- Sensor simulation (lidar, camera)
- Continuous-space movement (currently grid-cell-based)
- Web-based remote dashboard

---

## SIH Problem Statement Reference

**Problem Statement ID:** SIH26123  
**Title:** Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots in Smart Warehouses  
**Event:** Smart India Hackathon 2026

---

<div align="center">

**Built for SIH 2026 — Problem Statement 26123**  
*Zero collisions. No central server. Each robot decides for itself.*

</div>
