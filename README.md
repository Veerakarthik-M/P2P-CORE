# P2P-CORE 🤖
### Decentralized Peer-to-Peer Coordination for Autonomous Mobile Robot Fleets

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green?logo=pygame)
![License](https://img.shields.io/badge/License-MIT-yellow)
![SIH](https://img.shields.io/badge/SIH%202026-Problem%2026123-orange)
![Status](https://img.shields.io/badge/Status-Prototype-brightgreen)

**Smart India Hackathon 2026 | Problem Statement #26123**

*A fully working simulation of decentralized multi-robot coordination — no central server, no single point of failure.*

</div>

---

## 📌 Table of Contents

- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [Why This Matters](#-why-this-matters)
- [How the Simulation Works](#-how-the-simulation-works)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [P2P Communication](#-p2p-communication)
- [Conflict Resolution & Priority Scoring](#-conflict-resolution--priority-scoring)
- [Battery & Charging System](#-battery--charging-system)
- [Demo Scenarios](#-demo-scenarios-press-1-7)
- [Dashboard](#-dashboard-5-tabs)
- [Keyboard Controls](#-keyboard-controls)
- [Project Structure](#-project-structure)
- [Installation & Run](#-installation--run)
- [Tech Stack](#-tech-stack)
- [Results](#-results)
- [Future Work](#-future-work)

---

## ❗ The Problem

Modern smart warehouses use fleets of **Autonomous Mobile Robots (AMRs)** to transport goods efficiently. However, the dominant architecture today is **centralized** — every robot sends its position to a central server, which computes paths and sends back instructions.

This creates three critical vulnerabilities:

| Problem | Impact |
|---------|--------|
| 🌐 **Network Latency** | Every decision requires a cloud round-trip — robots slow down |
| 📶 **Wi-Fi Dead Zones** | A robot losing signal loses its ability to navigate |
| 💥 **Single Point of Failure** | Central server goes down → entire fleet stops |

As warehouse fleet sizes grow, these problems become **operationally catastrophic**.

---

## ✅ Our Solution

**P2P-CORE** implements a fully **decentralized coordination framework** where:

- Each robot runs **A\* path planning locally** — no server needed
- Robots communicate **directly with each other** (peer-to-peer) — no central coordinator
- Conflicts at narrow lanes are resolved through **local negotiation** using a priority scoring formula
- Dynamic obstacles trigger **instant local replanning**
- Battery management and charging is handled **autonomously** per robot

> The monitoring dashboard displays real-time status but **does NOT control robots**.  
> Robots operate correctly even when the dashboard goes offline.

---

## 💡 Why This Matters

| Traditional (Centralized) | P2P-CORE (Decentralized) |
|---------------------------|--------------------------|
| All decisions go through server | Each robot decides locally |
| Single point of failure | No single point of failure |
| Network-dependent | Edge-native, network-optional |
| Scales poorly (bottleneck) | Scales horizontally |
| Server down = fleet stops | Server down = fleet keeps running |

This directly maps to the **edge computing** paradigm — intelligence lives at the device, not in the cloud.

---

## ⚙️ How the Simulation Works

The simulation runs at **10 FPS** on a **22 × 28 grid** warehouse map.

### Every Tick (100ms):
1. `ConflictManager.resolve()` scans all robots' next 5 path cells for narrow-lane collisions
2. Each robot's `step()` is called — it moves one cell if the path is clear
3. Battery is drained based on movement state
4. If a robot is blocked for > 2.5s, the **Binary Assignment Resolver** fires
5. Dashboard renders the updated state

### Every Second:
- Each robot **broadcasts** a 9-field P2P state message to all others
- Robots read peer messages to anticipate each other's movement

### On Task Completion:
- Robot picks the next task from the shared task pool
- A\* plans a new path immediately

---

## 🏗️ System Architecture

```
                    ┌──────────────────────────────────┐
                    │         Warehouse Grid            │
                    │  22×28  |  4 Narrow Lanes        │
                    │  2 Charging Stations  |  Walls   │
                    └───────────────┬──────────────────┘
                                    │ shared read-only map
          ┌─────────────────────────┼────────────────────────┐
          │                         │                        │
     ┌────┴────┐               ┌────┴────┐              ┌────┴────┐
     │   R1    │               │   R2    │              │   R3    │
     │  A* ✓   │◄─────────────►│  A* ✓   │◄────────────►│  A* ✓   │
     │  Local  │   P2P every   │  Local  │  P2P every  │  Local  │
     │  State  │    1 second   │  State  │   1 second  │  State  │
     └────┬────┘               └────┬────┘              └────┬────┘
          │                         │                        │
          └─────────────────────────┼────────────────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │     ConflictManager (per tick)    │
                    │   Narrow-lane pre-emptive nego.   │
                    │   + Binary Assignment Resolver    │
                    └───────────────┬──────────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │    Dashboard (monitor only)       │
                    │  5-Tab Pygame UI — reads state    │
                    │  Does NOT send commands to robots │
                    └──────────────────────────────────┘
```

**Centralized components:** `MessageBus` (passive store-and-forward), `ConflictManager` (passive evaluator)  
**Decentralized:** Every Robot object makes its own movement, path planning, and negotiation decisions  

---

## 🚀 Features

### 🤖 3 Independent AMRs
Each robot is a fully autonomous agent with its own:
- Local A\* path planner (recalculates on demand)
- State machine (IDLE → MOVING → NEGOTIATING → ENTERING_LANE → IN_LANE → DELIVERING → COMPLETED)
- Priority score (updated every tick)
- Battery level (drains, triggers auto-charging)
- Event log (timestamped decisions)
- P2P message inbox/outbox

### 📡 Simulated P2P Communication
Every second each robot broadcasts:
```json
{
  "robot_id"     : "R1",
  "position"     : [5, 9],
  "target"       : [1, 26],
  "task_priority": 5,
  "urgency"      : 4,
  "wait_time"    : 0.0,
  "ETA"          : 4.5,
  "sim_time"     : 12.0,
  "state"        : "MOVING",
  "next_cells"   : [[5,10],[5,11],[5,12]],
  "battery"      : 91.4
}
```

### 🚦 Narrow-Lane Conflict Resolution
Four narrow lanes (choke points) exist in the warehouse. When 2+ robots' planned paths hit the same narrow cell:
1. Conflict detected 5 steps in advance
2. NEGOTIATE messages exchanged
3. Priority scores compared
4. Winner gets GRANT → enters lane
5. Loser gets YIELD → waits
6. Lane released when winner exits cell

### ⚖️ Anti-Starvation Priority Score
```
Score = 0.5 × TaskPriority + 0.3 × Urgency + 0.2 × WaitFactor

WaitFactor = min(wait_seconds / 30.0, 5.0)
```
A robot that keeps losing builds up wait time → score rises → eventually wins. **No robot is permanently blocked.**

### 🔄 Dynamic Obstacle Replanning
User can place/remove obstacles by clicking the grid. All robots immediately replan using A\* on the updated map.

### 🔋 Battery & Charging System
- Moving: drains at **1.5%/sec**
- Idle/waiting: drains at **0.1%/sec**
- At **30%** → LOW warning shown
- At **15%** → CRITICAL → robot autonomously navigates to nearest free charger
- Charging rate: **5%/sec**
- At **80%** → robot undocks and resumes saved task

### 📊 5-Tab Live Dashboard
Real-time monitoring with color-coded states, battery bars, P2P logs, conflict history.

### 🛡️ Zero Collisions
Before entering any cell, robots check if another robot occupies it. Narrow-lane negotiation happens preemptively. **Zero inter-robot collisions in all tested scenarios.**

---

## 📡 P2P Communication

P2P-CORE uses a `MessageBus` (simulated, would map to ZeroMQ/MQTT on real hardware).

### Message Types

| Type | Direction | Meaning |
|------|-----------|---------|
| `NEGOTIATE` | R1 → R2 | "I intend to enter Lane #0. My score: 3.70" |
| `GRANT` | R1 → R2 | "Lane #0 is mine. I proceed." |
| `YIELD` | R2 → R1 | "Acknowledged. Yielding. Waiting." |
| `PRIORITY` | R1 → R2 | "Binary assign: I=1, you=0. Clear my path." |
| `DETECT` | R2 → R1 | "You are blocking my path." |
| `REROUTE` | Rx → ALL | "Obstacle detected. Replanning." |
| `BATT_LOW` | Rx → ALL | "Battery CRITICAL. Heading to charger." |
| `CHARGING` | Rx → ALL | "Docked at C1. Charging." |
| `CHARGED` | Rx → ALL | "Charged to 80%. Resuming task." |
| `CTRL_ROOM` | SYS → ALL | "Control Room is now OFFLINE." |

---

## ⚔️ Conflict Resolution & Priority Scoring

### Priority Formula (from `priority.py`)
```python
Score = ALPHA * task_priority + BETA * urgency + GAMMA * wait_factor(wait_seconds)
# ALPHA = 0.5,  BETA = 0.3,  GAMMA = 0.2
# wait_factor = min(wait_seconds / 30.0, 5.0)
```

### Example — Scenario 2 (Narrow-Lane Conflict)
| Robot | Task Priority | Urgency | Wait | Score |
|-------|--------------|---------|------|-------|
| R1 | 5 | 4 | 0s | **3.70** ← wins |
| R2 | 4 | 3 | 0s | **2.90** ← yields |

### Binary Assignment (Deadlock Resolver)
Fires when a robot is WAITING > 2.5 seconds. Works like a binary constraint:
```
x(winner) = 1  → proceeds forward
y(loser)  = 0  → moved to backup cell, replans
x + y = 1      → exactly one robot gets access
```

---

## 🔋 Battery & Charging System

Two charging stations in the warehouse:
- **C1** → Row 1, Col 3 (top-left area)
- **C2** → Row 20, Col 24 (bottom-right area)

When a robot reaches CRITICAL battery level (15%):
1. Broadcasts `BATT_LOW` to fleet
2. Saves current task target
3. Navigates to nearest free charging station
4. Docks → state changes to `CHARGING`
5. Charges at 5%/sec until 80%
6. Broadcasts `CHARGED`
7. Resumes saved task from charger position

---

## 🎬 Demo Scenarios (Press 1–7)

| Key | Scenario | What It Demonstrates |
|-----|----------|----------------------|
| `1` | **Normal Operation** | All 3 robots navigate independently with local A\* |
| `2` | **Narrow-Lane Conflict** | R1 vs R2 at choke point — full NEGOTIATE→GRANT→YIELD sequence |
| `3` | **Starvation Test** | R3 (low priority) pre-loaded with 25s wait — score rises live until R3 eventually wins |
| `4` | **Deadlock Pressure** | All 3 robots converge on same bottleneck — binary assignment resolves it |
| `5` | **Dynamic Obstacle** | Pre-placed obstacles — robots replan around them using A\* |
| `6` | **Control-Room Failure** | Press C to toggle dashboard offline — robots keep coordinating via P2P |
| `7` | **Battery & Charging** | R3 starts at 12% — immediately routes to C1, docks, charges, resumes task |

---

## 📊 Dashboard (5 Tabs)

### Tab 1 — FLEET `[F1]`
- Live battery bars (green/orange/red) for all 3 robots
- State, position, priority score, wait time per robot
- P2P communication log (color-coded by message type)
- Charging station occupancy
- Fleet-wide metrics

### Tab 2/3/4 — R1 / R2 / R3 `[F2/F3/F4]`
- Current state (MOVING / WAITING / CHARGING / STALLED)
- Priority score breakdown with live formula values
- Battery bar + status (NORMAL / LOW / CRITICAL)
- Path progress (step X/Y, %)
- Timestamped decision log (last 8 events)

### Tab 5 — CONFLICT `[F5]`
- P2P Negotiation Log (always visible at top)
- Latest lane negotiation result (winner/loser/scores)
- Lane conflict history (last 4 events)

---

## ⌨️ Keyboard Controls

| Key | Action |
|-----|--------|
| `1` | Scenario 1: Normal Operation |
| `2` | Scenario 2: Narrow-Lane Conflict ⭐ |
| `3` | Scenario 3: Starvation Test |
| `4` | Scenario 4: Deadlock Pressure |
| `5` | Scenario 5: Dynamic Obstacle |
| `6` | Scenario 6: Control-Room Failure |
| `7` | Scenario 7: Battery & Charging |
| `SPACE` | Pause / Resume |
| `R` | Reset current scenario |
| `O` + click | Place / remove dynamic obstacle |
| `C` | Toggle control room online / offline |
| `TAB` | Cycle dashboard tabs |
| `F1`–`F5` | Jump to FLEET / R1 / R2 / R3 / CONFLICT tab |
| `Q` / `ESC` | Quit (saves results CSV) |

---

## 📁 Project Structure

```
P2P-CORE/
├── SIH26123/
│   ├── main.py           # Entry point, game loop, scenario switching
│   ├── robot.py          # Robot agent — state machine, A*, battery, events
│   ├── astar.py          # Pure A* path planner (Manhattan heuristic)
│   ├── warehouse.py      # 22×28 grid map, narrow lanes, charging stations
│   ├── conflict.py       # ConflictManager — narrow-lane negotiation
│   ├── priority.py       # Priority score formula & lane-owner selection
│   ├── communication.py  # MessageBus — P2P broadcast and negotiation log
│   ├── dashboard.py      # 5-tab Pygame monitoring UI
│   ├── scenarios.py      # 7 demo scenario factory functions
│   ├── metrics.py        # MetricsTracker — collisions, reroutes, wait, CSV
│   ├── logger.py         # SimLogger — conflict/reroute/task text log
│   └── config.py         # All constants — grid, colors, battery params, weights
├── health_check.py       # Module import + unit sanity tests
├── results/              # Auto-generated: simulation_results.csv, sim_log_*.txt
└── README.md
```

---

## 🛠️ Installation & Run

### Requirements
```bash
pip install pygame
```
> Python 3.11+ recommended. No other dependencies.

### Run
```bash
git clone https://github.com/Veerakarthik-M/P2P-CORE.git
cd P2P-CORE
pip install pygame
python SIH26123/main.py
```

### Health Check
```bash
python health_check.py
```
Verifies all modules import correctly and core functions work.

---

## 🧰 Tech Stack

| Technology | Role |
|-----------|------|
| **Python 3.11+** | Primary language — rapid prototyping, clean OOP |
| **Pygame** | 2D simulation window, rendering, keyboard/mouse input |
| **A\* (heapq)** | Optimal grid path planning — lightweight, edge-hardware ready |
| **MessageBus** | Simulated P2P mesh — maps to ZeroMQ/MQTT on real hardware |
| **CSV / txt logs** | Metrics export and event logging for analysis |

**Why Python + Pygame?**  
Python allows algorithmic clarity that evaluators can read and verify. Pygame provides a zero-dependency 2D simulation window. A\* on a 22×28 grid runs in < 1ms — suitable for Raspberry Pi 4 deployment.

---

## 📈 Results

Across all 7 scenarios tested:

| Metric | Result |
|--------|--------|
| Inter-robot collisions | **0** |
| Narrow-lane conflicts resolved | ✅ All |
| Starvation prevention | ✅ Demonstrated |
| Dynamic obstacle replanning | ✅ Instant |
| Control-room-offline operation | ✅ Uninterrupted |
| Battery auto-charging | ✅ Working |
| Metrics CSV export | ✅ Auto-saved |

> ⚠️ **Note:** The 20% task-completion-time improvement over stop-and-wait (from the SIH problem statement) is a **target benchmark**. The `MetricsTracker` has the `baseline_time` field built in for systematic comparison. Formal multi-run benchmarking is a planned next step.

---

## 🔮 Future Work

| Extension | Description |
|-----------|-------------|
| 🌐 Real P2P networking | Replace MessageBus with ZeroMQ / ROS2 for actual inter-process communication |
| 🖥️ Edge deployment | Deploy robot logic on Raspberry Pi 4 / Jetson Nano |
| 📏 Systematic benchmarking | Measure 20% improvement over stop-and-wait across ≥ 30 runs |
| 🤖 Larger fleets | Zone-based conflict management for 5+ robot fleets |
| 🛑 Robot failure handling | Full task reassignment when a robot fails permanently |
| 📡 Sensor simulation | Lidar/camera input simulation for path deviation detection |
| 🌍 Web dashboard | ROS2-compatible web UI replacing Pygame for remote monitoring |

---

## 👨‍💻 Team

**SIH 2026 — Problem Statement #26123**  
Decentralized Coordination and Collision-Avoidance Framework for Multi-Robot Fleet

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.

---

<div align="center">

**Built for Smart India Hackathon 2026**  
*Zero collisions. No central server. Pure edge intelligence.*

</div>
