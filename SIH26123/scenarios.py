# ============================================================
# scenarios.py  —  6 Demo Scenarios
# Each scenario resets robots and places them in a specific
# situation that demonstrates a feature.
# ============================================================
import random
from robot import Robot, MOVING, WAITING
from warehouse import TASK_POOL, ROBOT_CONFIGS


def _make_robots(warehouse):
    """Create the 3 default robots at their start positions."""
    robots = []
    configs = [
        ("R1", ROBOT_CONFIGS["R1"]["start"], 5, 4),
        ("R2", ROBOT_CONFIGS["R2"]["start"], 4, 3),
        ("R3", ROBOT_CONFIGS["R3"]["start"], 3, 2),
    ]
    for rid, start, pri, urg in configs:
        r = Robot(rid, start, pri, urg)
        r.calculate_score()
        robots.append(r)
    return robots


# ──────────────────────────────────────────────────────────────
def scenario_normal(warehouse):
    """
    Scenario 1: Normal operation.
    Each robot moves to its delivery goal independently.
    No forced conflicts.
    """
    warehouse.dynamic_obstacles.clear()
    robots = _make_robots(warehouse)
    grid   = warehouse.get_grid_for_astar()
    goals  = [ROBOT_CONFIGS["R1"]["goal"],
               ROBOT_CONFIGS["R2"]["goal"],
               ROBOT_CONFIGS["R3"]["goal"]]
    for r, g in zip(robots, goals):
        r.assign_task(g, grid)
    return robots, "Normal Operation"


# ──────────────────────────────────────────────────────────────
def scenario_narrow_conflict(warehouse):
    """
    Scenario 2: Narrow-lane conflict.
    R1 and R2 are placed so both must cross the same narrow lane.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    r1 = Robot("R1", (5, 1), task_priority=5, urgency=4)
    r2 = Robot("R2", (7, 1), task_priority=4, urgency=3)
    r3 = Robot("R3", (17, 1), task_priority=3, urgency=2)

    # Both R1 and R2 target cells across the narrow lane at (6,9)
    r1.assign_task((1, 26), grid, priority=5, urgency=4)
    r2.assign_task((1, 25), grid, priority=4, urgency=3)
    r3.assign_task((1,  7), grid, priority=3, urgency=2)

    return [r1, r2, r3], "Narrow-Lane Conflict"


# ──────────────────────────────────────────────────────────────
def scenario_starvation(warehouse):
    """
    Scenario 3: Starvation test.
    R3 starts with low priority but already has 25s accumulated wait
    so its score is pre-boosted. All three robots route through the same
    narrow lane so R3 actually enters WAITING/NEGOTIATING and its
    wait_time rises live on screen.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    r1 = Robot("R1", (5,  1), task_priority=5, urgency=5)
    r2 = Robot("R2", (7,  1), task_priority=5, urgency=4)
    r3 = Robot("R3", (11, 1), task_priority=2, urgency=1)

    # Assign tasks FIRST -- all targets require crossing narrow lane at (6,9)
    # so all three robots will actually compete for the same choke point
    r1.assign_task((1, 26), grid)
    r2.assign_task((1, 25), grid)
    r3.assign_task((1, 20), grid)   # also crosses the narrow-lane area

    # Set wait_time AFTER assign_task -- assign_task resets it to 0!
    # This is intentional: we pre-seed 25s so the score boost is already
    # visible at t=0, and then live negotiation adds more on top.
    r3.wait_time = 25.0
    r3.calculate_score()   # refresh score badge immediately

    return [r1, r2, r3], "Starvation Test"


# ──────────────────────────────────────────────────────────────
def scenario_deadlock(warehouse):
    """
    Scenario 4: Deadlock pressure.
    All 3 robots approach the same narrow lane simultaneously.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    r1 = Robot("R1", (5,  1), task_priority=4, urgency=4)
    r2 = Robot("R2", (7,  1), task_priority=4, urgency=3)
    r3 = Robot("R3", (11, 1), task_priority=3, urgency=4)

    r1.assign_task((1, 26), grid)
    r2.assign_task((1, 25), grid)
    r3.assign_task((1, 20), grid)

    return [r1, r2, r3], "Deadlock Pressure"


# ──────────────────────────────────────────────────────────────
def scenario_dynamic_obstacle(warehouse):
    """
    Scenario 5: A dynamic obstacle blocks a robot's path mid-route.
    The robot must replan using A*.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    robots = _make_robots(warehouse)
    goals  = [ROBOT_CONFIGS["R1"]["goal"],
               ROBOT_CONFIGS["R2"]["goal"],
               ROBOT_CONFIGS["R3"]["goal"]]
    for r, g in zip(robots, goals):
        r.assign_task(g, grid)

    # Place an obstacle on R1's likely path
    warehouse.add_obstacle(5, 13)
    warehouse.add_obstacle(5, 14)

    return robots, "Dynamic Obstacle"


# ──────────────────────────────────────────────────────────────
def scenario_ctrl_room_fail(warehouse):
    """
    Scenario 6: Control-room/Wi-Fi link failure.
    Robots continue coordinating via P2P.
    Dashboard shows CTRL ROOM: OFFLINE.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    robots = _make_robots(warehouse)
    goals  = [ROBOT_CONFIGS["R1"]["goal"],
               ROBOT_CONFIGS["R2"]["goal"],
               ROBOT_CONFIGS["R3"]["goal"]]
    for r, g in zip(robots, goals):
        r.assign_task(g, grid)

    # The ctrl-room-offline flag is handled by main.py
    return robots, "Control-Room Failure"


def scenario_battery_charging(warehouse):
    """
    Scenario 7: Battery & Charging demonstration.
    R3 starts at critical battery (12%) so it immediately heads to nearest
    charging station.  R1 and R2 operate normally but with moderate battery.
    After R3 charges to 80% it resumes its original task.
    """
    warehouse.dynamic_obstacles.clear()
    grid = warehouse.get_grid_for_astar()

    # Override BATTERY_INIT for this scenario via direct attribute assignment
    r1 = Robot("R1", (1,  1), task_priority=5, urgency=4)
    r2 = Robot("R2", (1, 26), task_priority=4, urgency=3)
    r3 = Robot("R3", (20, 1), task_priority=3, urgency=2)

    # Force battery levels for the demo
    r1.battery = 85.0
    r2.battery = 55.0
    r3.battery = 12.0   # CRITICAL — will head to charger immediately

    # Update battery_status to match
    from robot import _battery_status
    r1.battery_status = _battery_status(r1.battery)
    r2.battery_status = _battery_status(r2.battery)
    r3.battery_status = _battery_status(r3.battery)

    # Assign normal tasks (R3 will interrupt its task to charge)
    r1.assign_task((20, 26), grid)
    r2.assign_task((20,  1), grid)
    r3.assign_task((1,  26), grid)   # R3 will detour to charger first

    return [r1, r2, r3], "Battery & Charging"


SCENARIOS = [
    scenario_normal,
    scenario_narrow_conflict,
    scenario_starvation,
    scenario_deadlock,
    scenario_dynamic_obstacle,
    scenario_ctrl_room_fail,
    scenario_battery_charging,
]
