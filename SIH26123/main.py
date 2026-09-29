# ============================================================
# main.py  —  SIH26123 Main Simulation Entry Point
#
# Controls:
#   SPACE       → pause / resume
#   1-6         → switch scenario
#   TAB         → cycle dashboard views (FLEET/R1/R2/R3/CONFLICT)
#   F1-F5       → direct-jump to view
#   O           → place/remove obstacle (click on grid)
#   C           → toggle control-room online/offline
#   R           → reset current scenario
#   Q / Escape  → quit
# ============================================================
import pygame
import sys
import time
import random

from config      import FPS, CELL_SIZE, MSG_INTERVAL, COLS, ROWS
from warehouse   import Warehouse
from robot       import (Robot, IDLE, MOVING, COMPLETED, WAITING, CHARGING,
                         STALLED, STALL_SECS, ENTERING_LANE, IN_LANE)
from communication import MessageBus, build_message
from conflict    import ConflictManager
from metrics     import MetricsTracker
from dashboard   import Dashboard
from scenarios   import SCENARIOS
from logger      import SimLogger


def run_simulation(scenario_idx=0):
    # ── Init subsystems ────────────────────────────────────────
    warehouse      = Warehouse()
    msg_bus        = MessageBus()
    metrics        = MetricsTracker()
    sim_logger     = SimLogger()

    # Load first scenario
    load_scenario_fn = SCENARIOS[scenario_idx]
    robots, scenario_name = load_scenario_fn(warehouse)

    conflict_mgr   = ConflictManager(warehouse)
    dash           = Dashboard(warehouse, scenario_name)

    # ── Simulation State ──────────────────────────────────────
    paused          = False
    ctrl_room_online= True
    sim_time        = 0.0
    last_msg_time   = 0.0
    obstacle_mode   = False   # True → next click places/removes obstacle
    current_scenario= scenario_idx

    # Charging station occupancy: {station_id: robot_id or None}
    charger_occupancy = {cs["id"]: None for cs in warehouse.charging_stations}

    def reset(idx):
        nonlocal robots, conflict_mgr, sim_time, last_msg_time
        nonlocal scenario_name, paused, ctrl_room_online, charger_occupancy
        msg_bus.clear()
        metrics.__init__()
        warehouse.dynamic_obstacles.clear()
        robots, scenario_name = SCENARIOS[idx](warehouse)
        conflict_mgr  = ConflictManager(warehouse)
        dash.scenario_name = scenario_name
        pygame.display.set_caption(f"SIH26123 – AMR Fleet Simulation  [{scenario_name}]")
        sim_time      = 0.0
        last_msg_time = 0.0
        paused        = False
        ctrl_room_online = True if idx != 5 else False   # scenario 6 starts offline
        charger_occupancy = {cs["id"]: None for cs in warehouse.charging_stations}

    reset(scenario_idx)

    # ── Main Loop ─────────────────────────────────────────────
    running = True
    prev_tick = time.time()

    while running:
        now   = time.time()
        dt    = now - prev_tick
        prev_tick = now

        # ── Event Handling ────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    reset(current_scenario)
                elif event.key == pygame.K_c:
                    ctrl_room_online = not ctrl_room_online
                    # Log the control room state change
                    status = "ONLINE" if ctrl_room_online else "OFFLINE"
                    msg_bus.log_negotiation(
                        "SYSTEM", "ALL", "CTRL_ROOM",
                        sim_time, f"Control Room is now {status}"
                    )
                    for robot in robots:
                        robot.log_event(f"Control Room → {status}", sim_time)
                elif event.key == pygame.K_o:
                    obstacle_mode = not obstacle_mode
                elif event.key == pygame.K_TAB:
                    dash.cycle_tab()
                elif event.key == pygame.K_F1:
                    dash.active_tab = "FLEET"
                elif event.key == pygame.K_F2:
                    dash.active_tab = "R1"
                elif event.key == pygame.K_F3:
                    dash.active_tab = "R2"
                elif event.key == pygame.K_F4:
                    dash.active_tab = "R3"
                elif event.key == pygame.K_F5:
                    dash.active_tab = "CONFLICT"
                elif pygame.K_1 <= event.key <= pygame.K_7:
                    current_scenario = event.key - pygame.K_1
                    reset(current_scenario)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if mx >= COLS * CELL_SIZE:
                    dash.handle_click(mx, my)
                elif obstacle_mode and mx < COLS * CELL_SIZE:
                    gc = mx // CELL_SIZE
                    gr = my // CELL_SIZE
                    warehouse.toggle_obstacle(gr, gc)
                    # Force all robots to replan
                    grid = warehouse.get_grid_for_astar()
                    other_pos = {r.position for r in robots}
                    for robot in robots:
                        if robot.target:
                            robot.replan(grid, other_pos - {robot.position})
                            sim_logger.log_reroute(robot.robot_id, robot.position)

        # ── Simulation Step ───────────────────────────────────
        if not paused:
            sim_time += dt
            grid = warehouse.get_grid_for_astar()
            other_positions = {r.position for r in robots}

            # Give each robot the current simulation time
            for robot in robots:
                robot.update_sim_time(sim_time)

            # 1. Conflict detection & lane negotiation (pass msg_bus for P2P logging)
            conflict_mgr.resolve(robots, sim_time, msg_bus)

            # 2. P2P Message broadcast (every MSG_INTERVAL seconds)
            #    Per ideation doc Section 8: publish every 1 second
            #    Control Room OFFLINE = robots STILL broadcast to each other
            #    (this proves decentralized operation — dashboard just can't send commands)
            if sim_time - last_msg_time >= MSG_INTERVAL:
                last_msg_time = sim_time
                for robot in robots:
                    msg = build_message(robot, sim_time)
                    msg_bus.broadcast(robot.robot_id, msg)
                    robot.messages_sent += 1

                # Each robot reads messages from others
                for robot in robots:
                    others_msgs = msg_bus.get_messages(robot.robot_id)
                    robot.messages_recv += len(others_msgs)

            # 3. Move robots
            # Re-snapshot positions after EACH move so robots don't
            # phantom-block each other when positions change mid-loop
            for robot in robots:
                # Fresh snapshot excluding this robot's own cell
                current_others = {r.position for r in robots
                                  if r.robot_id != robot.robot_id}
                prev_state = robot.state
                moved = robot.step(grid, current_others, dt)

                # ── Battery drain ────────────────────────────────────
                robot.update_battery(dt, is_moving=moved)

                # ── Stall detection ───────────────────────────────────
                # Track how long position is unchanged while robot claims MOVING.
                # display_state property returns STALLED for display when threshold hit.
                # We do NOT mutate robot.state here — that would break the deadlock
                # resolver (which checks for WAITING state) and the conflict manager.
                if robot.position != robot._last_position:
                    robot._last_position = robot.position
                    robot._stall_timer   = 0.0
                elif robot.state in (MOVING, ENTERING_LANE, IN_LANE):
                    robot._stall_timer += dt
                else:
                    robot._stall_timer = 0.0

                # ── Charger arrival detection (MUST run before battery check) ──
                # When _on_arrive() fires at a charger cell it sets state=IDLE.
                # We must dock here BEFORE the battery-CRITICAL check, otherwise
                # the battery check re-calls navigate_to_charger() (state=MOVING)
                # and the charger detection never sees state==IDLE → infinite loop.
                if robot.state == IDLE:
                    for cs in warehouse.charging_stations:
                        if robot.position == cs["pos"]:
                            if charger_occupancy[cs["id"]] in (None, robot.robot_id):
                                charger_occupancy[cs["id"]] = robot.robot_id
                                robot.start_charging(cs["id"])
                                msg_bus.log_negotiation(
                                    robot.robot_id, "ALL", "CHARGING", sim_time,
                                    f"Docked at {cs['id']} — charging ({robot.battery:.1f}%)"
                                )
                            else:
                                # Station occupied — redirect to nearest free one
                                other = _find_nearest_charger(
                                    robot, warehouse.charging_stations,
                                    charger_occupancy, robots
                                )
                                if other and other[1] != robot.position:
                                    robot.navigate_to_charger(other[1], other[0], grid)
                            break

                # ── Tick charging robots ─────────────────────────────────
                if robot.state == CHARGING:
                    done = robot.tick_charging(dt)
                    if done:
                        if robot.charging_station_id:
                            charger_occupancy[robot.charging_station_id] = None
                        robot.resume_after_charging(grid)
                        msg_bus.log_negotiation(
                            robot.robot_id, "ALL", "CHARGED", sim_time,
                            f"Fully charged ({robot.battery:.1f}%) — resuming task"
                        )

                # ── Auto-navigate to charger if CRITICAL (runs AFTER dock check) ─
                # Guards: not already headed, not CHARGING, not physically at a charger
                at_charger = any(robot.position == cs["pos"]
                                 for cs in warehouse.charging_stations)
                if (robot.battery_status == "CRITICAL"
                        and not robot._headed_to_charger
                        and robot.state != CHARGING
                        and not at_charger):
                    nearest = _find_nearest_charger(
                        robot, warehouse.charging_stations, charger_occupancy, robots
                    )
                    if nearest:
                        cid, cpos = nearest
                        robot.navigate_to_charger(cpos, cid, grid)
                        msg_bus.log_negotiation(
                            robot.robot_id, "ALL", "BATT_LOW", sim_time,
                            f"Battery CRITICAL {robot.battery:.1f}% → navigating to {cid}"
                        )

                # Log state transitions
                if robot.state != prev_state and robot.state == WAITING:
                    # Find which robot is blocking
                    if robot.path and robot.path_index + 1 < len(robot.path):
                        blocked_cell = robot.path[robot.path_index + 1]
                        blocker = next(
                            (r for r in robots
                             if r.robot_id != robot.robot_id and r.position == blocked_cell),
                            None
                        )
                        if blocker:
                            robot.log_event(
                                f"Blocked by {blocker.robot_id} at {blocked_cell}", sim_time
                            )
                            msg_bus.log_negotiation(
                                robot.robot_id, blocker.robot_id,
                                "DETECT", sim_time,
                                f"You are blocking my path at {blocked_cell}. Waiting."
                            )

                # Dynamic obstacle on path → replan
                if robot.path and robot.path_index < len(robot.path):
                    next_c = robot.path[robot.path_index + 1] \
                             if robot.path_index + 1 < len(robot.path) else None
                    if next_c and not warehouse.is_walkable(*next_c):
                        robot.replan(grid, current_others)
                        sim_logger.log_reroute(robot.robot_id, robot.position)
                        msg_bus.log_negotiation(
                            robot.robot_id, "ALL", "REROUTE", sim_time,
                            f"Obstacle at {next_c}. Replanning route."
                        )

                # If IDLE with no tasks yet assigned, give first task
                # (Don't assign tasks to robots that just arrived at charger)
                if robot.state == IDLE and robot.target is None and robot.state != CHARGING:
                    _assign_next_task(robot, warehouse, robots, sim_time)

                # Robot completed a task → give a new one
                if (robot.state == IDLE and robot.tasks_completed > 0
                        and robot.target is None and robot.state != CHARGING
                        and not robot._headed_to_charger):
                    _assign_next_task(robot, warehouse, robots, sim_time)

                # ── Always keep score up to date every tick ───────────
                # IDLE robots with no task get score=0 so they always
                # yield to active robots in binary assignment.
                if robot.state == IDLE and robot.target is None:
                    robot.score = 0.0   # zero — gets out of the way
                else:
                    robot.calculate_score()

            # Collision counter (any two robots sharing a cell)
            for i, robot in enumerate(robots):
                for j in range(i + 1, len(robots)):
                    if robots[i].position == robots[j].position:
                        robots[i].collisions += 1

            # 3b. CELL-LEVEL DEADLOCK RESOLVER
            #     When 2 robots block each other on a regular path (not narrow lane),
            #     use Priority Score: higher score STAYS, lower score REROUTES.
            #     Per ideation doc: "robots negotiate before entering" — same principle
            #     applies to any path conflict, not just narrow lanes.
            _resolve_cell_deadlocks(robots, warehouse, msg_bus, sim_time)

            # 4. Log any new conflict events
            if conflict_mgr.latest_event:
                evt = conflict_mgr.latest_event
                if not hasattr(evt, '_logged'):
                    sim_logger.log_conflict(evt)
                    evt._logged = True

            # 5. Update metrics
            metrics.update(robots, sim_time)

        # ── Draw ──────────────────────────────────────────────
        dash.draw(robots, metrics, msg_bus, conflict_mgr,
                  sim_time, paused, ctrl_room_online, charger_occupancy)

    # ── Cleanup ───────────────────────────────────────────────
    metrics.save_csv(robots, sim_time)
    sim_logger.save()
    dash.quit()


# ── Charging Station Helpers ──────────────────────────────────

def _find_nearest_charger(robot, charging_stations, charger_occupancy, all_robots):
    """
    Return (station_id, station_pos) of the nearest available charging station,
    or None if all are occupied by other robots currently CHARGING.
    """
    best_dist  = float("inf")
    best_entry = None
    r, c = robot.position
    for cs in charging_stations:
        cid  = cs["id"]
        cpos = cs["pos"]
        occupant = charger_occupancy.get(cid)
        # Free if unoccupied or occupied by this robot
        if occupant not in (None, robot.robot_id):
            occupant_robot = next(
                (rb for rb in all_robots if rb.robot_id == occupant), None
            )
            if occupant_robot and occupant_robot.state == "CHARGING":
                continue   # genuinely occupied
            else:
                charger_occupancy[cid] = None   # stale entry, free it
        dist = abs(cpos[0] - r) + abs(cpos[1] - c)
        if dist < best_dist:
            best_dist  = dist
            best_entry = (cid, cpos)
    return best_entry


# ── Cell-Level Deadlock Resolver (Binary Assignment) ──────────
# Logic (like MILP binary assignment):
#   x + y = 1  (exactly one robot gets priority = 1)
#   x = 1 (winner, higher score): MOVES FORWARD on its path
#   y = 0 (loser,  lower  score): PHYSICALLY BACKS UP to clear path,
#                                  then replans a route around winner
#
# Why just sending YIELD messages doesn't work: both robots are
# physically occupying cells that block each other. The loser must
# MOVE OUT OF THE WAY first before the winner can proceed.

DEADLOCK_THRESHOLD = 2.5   # seconds of waiting before triggering

def _find_backup_cell(robot, warehouse, all_robots):
    """
    Find a safe cell the robot can immediately step back into.
    Priority order:
      1. Previous cell on its own path (step backward 1 cell)
      2. Any adjacent walkable cell not occupied by another robot
    Returns the backup (row, col) or None if truly trapped.
    """
    other_positions = {r.position for r in all_robots
                       if r.robot_id != robot.robot_id}

    # Option 1: step backward along own path
    if robot.path and robot.path_index > 0:
        back_cell = robot.path[robot.path_index - 1]
        if (back_cell not in other_positions
                and warehouse.is_walkable(*back_cell)):
            return back_cell

    # Option 2: any adjacent open cell
    r, c = robot.position
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        cell = (r + dr, c + dc)
        if (warehouse.is_walkable(*cell)
                and cell not in other_positions):
            return cell

    return None   # truly cornered — can't back up


def _resolve_cell_deadlocks(robots, warehouse, msg_bus, sim_time):
    """
    Binary assignment: when robots block each other, assign x=1 (move)
    to higher-score robot and y=0 (back up) to lower-score robot.

    Step 1: Score comparison → winner (x=1) and loser (y=0)
    Step 2: Loser physically steps to a backup cell, clearing winner's path
    Step 3: Winner resumes moving forward
    Step 4: Loser replans from backup cell around winner's path
            If no route exists → loser gets a new task in a different area
    """
    resolved = set()

    for r1 in robots:
        if r1.robot_id in resolved:
            continue
        # Only trigger after robot has been WAITING long enough
        if r1.state != WAITING or r1.wait_time < DEADLOCK_THRESHOLD:
            continue
        if not r1.path or r1.path_index + 1 >= len(r1.path):
            continue

        # Who is physically sitting in r1's next cell?
        blocked_cell = r1.path[r1.path_index + 1]
        blocker = next(
            (r for r in robots
             if r.robot_id != r1.robot_id and r.position == blocked_cell),
            None
        )
        if blocker is None or blocker.robot_id in resolved:
            continue

        # ── Binary Assignment: Score decides x=1, y=0 ──────
        # Special rule: IDLE robot with no task ALWAYS yields to active robot
        r1_idle  = (r1.state      == IDLE and r1.target      is None)
        blk_idle = (blocker.state == IDLE and blocker.target is None)

        if r1_idle and not blk_idle:
            winner, loser = blocker, r1   # r1 is loitering — must yield
        elif blk_idle and not r1_idle:
            winner, loser = r1, blocker   # blocker is loitering — must yield
        else:
            # Both active (or both idle) — use Priority Score
            r1.calculate_score()
            blocker.calculate_score()
            if r1.score > blocker.score:
                winner, loser = r1, blocker
            elif blocker.score > r1.score:
                winner, loser = blocker, r1
            else:
                # Tie-break: smaller robot ID wins
                winner, loser = (r1, blocker) if r1.robot_id < blocker.robot_id \
                                else (blocker, r1)

        # ── P2P Message: announce binary assignment ─────────
        msg_bus.log_negotiation(
            winner.robot_id, loser.robot_id, "PRIORITY", sim_time,
            f"Binary assign: I=1 (score {winner.score:.2f}), you=0. Clear my path."
        )
        msg_bus.log_negotiation(
            loser.robot_id, winner.robot_id, "YIELD", sim_time,
            f"Assigned=0 (score {loser.score:.2f}). Backing up to clear path."
        )

        # ── STEP 1: Loser physically backs up ──────────────
        backup_cell = _find_backup_cell(loser, warehouse, robots)

        if backup_cell is not None:
            # Move the loser physically to the backup cell NOW
            loser.position = backup_cell
            loser.state = MOVING
            loser._cell_blocked_timer = 0.0
            loser.wait_time = 0.0    # reset wait since we resolved it

            # ── STEP 2: Loser replans from backup cell around winner ──
            grid = warehouse.get_grid_for_astar()
            # Reserve winner's current cell + next 5 steps of winner's path
            reserved = {winner.position}
            if winner.path:
                for ci in range(winner.path_index,
                                min(winner.path_index + 5, len(winner.path))):
                    reserved.add(winner.path[ci])

            # Replan loser from backup_cell → loser's target
            if loser.target:
                from astar import astar
                new_path = astar(grid, backup_cell, loser.target, reserved)
                if new_path and len(new_path) > 1:
                    loser.path = new_path
                    loser.path_index = 0
                    loser.log_event(
                        f"⚡ Backed up to {backup_cell}. New route "
                        f"around {winner.robot_id} ({len(new_path)} steps)", sim_time
                    )
                else:
                    # No route around winner → get a completely new task
                    loser.log_event(
                        f"⚡ Backed up. No route around {winner.robot_id}."
                        f" Getting new task.", sim_time
                    )
                    _assign_next_task(loser, warehouse, robots, sim_time)
        else:
            # Truly cornered — force a new task in a different location
            loser.log_event(
                f"⚡ Cornered, can't back up. Abandoning task.", sim_time
            )
            loser.wait_time = 0.0
            _assign_next_task(loser, warehouse, robots, sim_time)

        # ── STEP 3: Winner moves forward (path is now clear) ──
        winner.state = MOVING
        winner._cell_blocked_timer = 0.0
        winner.wait_time = 0.0
        winner.log_event(
            f"⚡ Won path conflict vs {loser.robot_id} "
            f"({winner.score:.2f} > {loser.score:.2f}). Proceeding.", sim_time
        )

        resolved.add(r1.robot_id)
        resolved.add(blocker.robot_id)


# ── Task Cycling ──────────────────────────────────────────────
from warehouse import TASK_POOL as _TASK_POOL

def _assign_next_task(robot, warehouse, all_robots, sim_time=0.0):
    """
    Assign a random task from TASK_POOL that is not currently
    someone else's target.
    """
    occupied = {r.target for r in all_robots if r.target}
    candidates = [t for t in _TASK_POOL if t not in occupied]
    if not candidates:
        candidates = _TASK_POOL[:]
    target = random.choice(candidates)
    grid   = warehouse.get_grid_for_astar()
    robot.assign_task(target, grid)


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    idx = 0
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1]) - 1   # user passes 1-6
        except ValueError:
            pass
    run_simulation(scenario_idx=max(0, min(idx, 5)))
