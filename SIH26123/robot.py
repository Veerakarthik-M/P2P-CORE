# ============================================================
# robot.py  —  Robot Agent
# Each robot owns its own state, path, and decision logic.
# ============================================================
from astar import astar
from priority import priority_score, choose_lane_owner
from config import (MOVE_TICKS, FPS, MSG_INTERVAL,
                    BATTERY_INIT, BATTERY_DRAIN_MOVING, BATTERY_DRAIN_IDLE,
                    BATTERY_LOW, BATTERY_CRITICAL,
                    BATTERY_CHARGE_RATE, BATTERY_CHARGE_TARGET)

# How long (seconds) a robot waits before trying to replan around a blocker
# NOTE: The deadlock resolver fires at 2.5s — keep this above that
# so the resolver handles it first, not the robot itself randomly replanning.
REPLAN_WAIT_THRESHOLD = 4.0

# Robot states
IDLE                = "IDLE"
MOVING              = "MOVING"
APPROACHING_CONFLICT= "APPROACHING_CONFLICT"
NEGOTIATING         = "NEGOTIATING"
WAITING             = "WAITING"
ENTERING_LANE       = "ENTERING_LANE"
IN_LANE             = "IN_LANE"
DELIVERING          = "DELIVERING"
COMPLETED           = "COMPLETED"
CHARGING            = "CHARGING"          # robot is docked and charging
STALLED             = "STALLED"           # MOVING but position unchanged

STALL_SECS = 4.0    # seconds of no movement while MOVING → show as STALLED

# Battery status labels
BATT_NORMAL   = "NORMAL"
BATT_LOW      = "LOW"
BATT_CRITICAL = "CRITICAL"


def _battery_status(pct: float) -> str:
    if pct >= BATTERY_LOW:
        return BATT_NORMAL
    elif pct >= BATTERY_CRITICAL:
        return BATT_LOW
    return BATT_CRITICAL



class Robot:
    def __init__(self, robot_id: str, start: tuple,
                 task_priority: int = 3, urgency: int = 3):
        self.robot_id       = robot_id
        self.position       = start          # (row, col)
        self.start          = start
        self.target         = None           # (row, col)
        self.path           = []             # list of (row, col)
        self.path_index     = 0

        self.task_priority  = task_priority  # 1-5
        self.urgency        = urgency        # 1-5
        self.wait_time      = 0.0            # seconds waited in conflicts
        self.state          = IDLE

        # Scoring cache (updated each negotiation)
        self.score          = 0.0

        # Internal movement ticker
        self._move_ticker   = 0
        self._msg_timer     = 0.0

        # Task tracking
        self.tasks_completed= 0
        self.total_wait     = 0.0
        self.collisions     = 0
        self.reroutes       = 0
        self.messages_sent  = 0
        self.messages_recv  = 0

        # Lane negotiation
        self.lane_reserved_by = None        # robot_id currently in the lane
        self.waiting_for      = None        # robot_id we are deferring to

        # Deadlock / cell-block recovery
        self._cell_blocked_timer = 0.0      # how long we've been blocked on a cell

        # Event log — stores recent robot-specific events with timestamps
        self.event_log       = []           # list of event strings
        self._sim_time       = 0.0          # current simulation time (updated from main loop)

        # ── Battery ────────────────────────────────────────────
        self.battery         = float(BATTERY_INIT.get(robot_id, 80))
        self.battery_status  = _battery_status(self.battery)

        # Charging station management
        self.charging_station_id  = None   # which station we're docked at
        self._pre_charge_target   = None   # task target remembered before charging
        self._pre_charge_state    = IDLE   # state before charging
        self._headed_to_charger   = False  # True when navigating toward charger
        self._charger_pos         = None   # position of the station we're going to

        # Stall detection — position stability tracking
        self._last_position = self.position
        self._stall_timer   = 0.0         # seconds position has been unchanged while MOVING

    # ----------------------------------------------------------
    # Simulation time tracking
    # ----------------------------------------------------------
    def update_sim_time(self, sim_time: float):
        """Called each tick from main loop to keep robot aware of sim clock."""
        self._sim_time = sim_time

    # ----------------------------------------------------------
    @property
    def display_state(self) -> str:
        """
        State string for display purposes only.
        Returns STALLED if robot has been MOVING but position-frozen for
        STALL_SECS — without mutating self.state (which would break the
        deadlock resolver and conflict manager).
        """
        if self.state in (MOVING, ENTERING_LANE, IN_LANE) and self._stall_timer >= STALL_SECS:
            return STALLED
        return self.state

    # ----------------------------------------------------------
    # Event Logging
    # ----------------------------------------------------------
    def log_event(self, text: str, sim_time: float = None):
        """Append timestamped entry to robot's local event log."""
        t = sim_time if sim_time is not None else self._sim_time
        entry = f"[{t:.1f}s] {text}"
        self.event_log.append(entry)
        if len(self.event_log) > 20:
            self.event_log.pop(0)

    # ----------------------------------------------------------
    # Path Planning
    # ----------------------------------------------------------
    def plan_path(self, grid, reserved=None):
        """Run A* from current position to self.target."""
        if self.target is None:
            return
        new_path = astar(grid, self.position, self.target, reserved or set())
        if new_path:
            self.path       = new_path
            self.path_index = 0
        else:
            # No path found — stay put, will retry next tick
            self.path = []

    def replan(self, grid, reserved=None):
        """Replan path (obstacle detected or lane blocked)."""
        self.reroutes += 1
        self.plan_path(grid, reserved)
        # Only log meaningful replans (not empty failures)
        if self.path:
            self.log_event(f"Replanned route ({len(self.path)} steps)")

    # ----------------------------------------------------------
    # Battery management
    # ----------------------------------------------------------
    def update_battery(self, dt: float, is_moving: bool):
        """Drain battery each tick. Returns True if status changed."""
        if self.state == CHARGING:
            return False   # no drain while charging
        drain = BATTERY_DRAIN_MOVING if is_moving else BATTERY_DRAIN_IDLE
        self.battery = max(0.0, self.battery - drain * dt)
        new_status   = _battery_status(self.battery)
        changed = (new_status != self.battery_status)
        if changed:
            self.battery_status = new_status
            self.log_event(f"🔋 Battery {new_status}: {self.battery:.1f}%")
        return changed

    def start_charging(self, station_id: str):
        """Called by main loop when robot arrives at a charger."""
        if self.state == CHARGING:
            return
        # Only save target if navigate_to_charger() hasn't already saved it.
        # (navigate_to_charger sets _pre_charge_target = original task
        #  before overwriting self.target with the charger pos)
        if not self._pre_charge_target and self.target:
            self._pre_charge_target = self.target
        self._pre_charge_state  = self.state
        self.charging_station_id= station_id
        self._headed_to_charger = False
        self._charger_pos       = None
        self.state              = CHARGING
        self.target             = None
        self.path               = []
        self.log_event(f"⚡ Docked at {station_id} — charging ({self.battery:.1f}%)")

    def tick_charging(self, dt: float) -> bool:
        """
        Called each tick when state == CHARGING.
        Returns True when charging is complete.
        """
        self.battery = min(100.0, self.battery + BATTERY_CHARGE_RATE * dt)
        self.battery_status = _battery_status(self.battery)
        if self.battery >= BATTERY_CHARGE_TARGET:
            self.log_event(
                f"⚡ Charging complete at {self.charging_station_id}: {self.battery:.1f}%"
            )
            return True
        return False

    def resume_after_charging(self, grid):
        """Called when charging finishes — robot returns to its saved task."""
        prev_station = self.charging_station_id
        self.charging_station_id = None
        self.battery_status = _battery_status(self.battery)
        if self._pre_charge_target:
            self.target = self._pre_charge_target
            self._pre_charge_target = None
            self.state  = MOVING
            self.plan_path(grid)
            self.log_event(f"▶ Resuming task → {self.target}")
        else:
            self.state  = IDLE
            self.target = None

    def navigate_to_charger(self, station_pos: tuple, station_id: str, grid):
        """
        Interrupt current task, navigate to nearest charger.
        Saves current target so we can resume after charging.
        """
        if self._headed_to_charger or self.state == CHARGING:
            return
        # Remember what we were doing (only save real task targets, not charger positions)
        if self.target and self.target != station_pos:
            self._pre_charge_target = self.target
        self._headed_to_charger = True
        self._charger_pos       = station_pos
        self.target             = station_pos
        self.state              = MOVING
        self.plan_path(grid)
        self.log_event(
            f"🔋 {self.battery:.1f}% CRITICAL → heading to {station_id} {station_pos}"
        )

    # ----------------------------------------------------------
    # Communication
    # ----------------------------------------------------------
    def calculate_score(self):
        self.score = priority_score(self.task_priority,
                                    self.urgency,
                                    self.wait_time)
        return self.score

    def eta(self) -> float:
        """Estimated steps remaining on current path (in seconds)."""
        remaining = max(0, len(self.path) - self.path_index - 1)
        return round(remaining / max(FPS / MOVE_TICKS, 1), 2)

    # ----------------------------------------------------------
    # Movement
    # ----------------------------------------------------------
    def step(self, grid, other_positions: set, dt: float):
        """
        Called every simulation tick.
        dt = seconds per tick (1/FPS).

        Returns True if robot moved this tick.
        """
        if self.state in (IDLE, COMPLETED, CHARGING):
            return False

        # Accumulate wait time when waiting for lane negotiation
        if self.state == WAITING:
            self.wait_time          += dt
            self.total_wait         += dt
            self._cell_blocked_timer+= dt
            self.calculate_score()
            # If stuck too long waiting for another robot's CELL (not lane),
            # replan around the blocker
            if self._cell_blocked_timer > REPLAN_WAIT_THRESHOLD and self.waiting_for is None:
                self.replan(grid, other_positions)
                if self.path:
                    self.state = MOVING
                    self._cell_blocked_timer = 0.0
                elif self._cell_blocked_timer > 5.0:
                    # Abandon blocked target if completely stuck in corner
                    self.log_event(f"Abandoned blocked target {self.target}")
                    self.target = None
                    self.state = IDLE
                    self.path = []
                    self._cell_blocked_timer = 0.0
            return False

        # NEGOTIATING robots just wait for conflict manager to assign winner
        if self.state == NEGOTIATING:
            self.wait_time  += dt
            self.total_wait += dt
            return False

        if self.state not in (MOVING, ENTERING_LANE, IN_LANE, DELIVERING):
            return False

        # Reset block timer when moving freely
        self._cell_blocked_timer = 0.0

        # Throttle movement speed
        self._move_ticker += 1
        if self._move_ticker < MOVE_TICKS:
            return False
        self._move_ticker = 0

        # If path is empty or exhausted — replan
        if not self.path:
            self.replan(grid, other_positions)
            return False

        # Advance one cell along path
        next_idx = self.path_index + 1
        if next_idx >= len(self.path):
            # Reached target
            self._on_arrive()
            return True

        next_cell = self.path[next_idx]

        # Collision check: don't step into another robot's cell
        if next_cell in other_positions:
            # Wait briefly, then replan around the blocker
            self._cell_blocked_timer += dt
            if self._cell_blocked_timer > REPLAN_WAIT_THRESHOLD:
                self._cell_blocked_timer = 0.0
                self.replan(grid, other_positions)
            else:
                self.state      = WAITING
                self.wait_time += dt
                self.total_wait+= dt
            return False

        self.position   = next_cell
        self.path_index = next_idx
        return True

    def _on_arrive(self):
        if self.state in (DELIVERING, MOVING, ENTERING_LANE, IN_LANE):
            if self._headed_to_charger:
                # Arrival at charger — main loop will call start_charging()
                self._headed_to_charger = False
                self.state = IDLE
            else:
                self.tasks_completed += 1
                self.log_event(f"✓ Completed task #{self.tasks_completed} at {self.position}")
                self.state  = IDLE
                self.target = None
                self.path   = []
                self.path_index = 0
                self.wait_time  = 0.0   # reset after task completes

    # ----------------------------------------------------------
    # Task Assignment
    # ----------------------------------------------------------
    def assign_task(self, target: tuple, grid,
                    priority: int = None, urgency: int = None):
        if priority is not None:
            self.task_priority = priority
        if urgency is not None:
            self.urgency = urgency
        self.target    = target
        self.wait_time = 0.0
        self.state     = MOVING
        self.plan_path(grid)
        self.log_event(f"→ New task: deliver to {target} (P:{self.task_priority} U:{self.urgency})")

    # ----------------------------------------------------------
    def __repr__(self):
        return (f"Robot({self.robot_id} pos={self.position} "
                f"state={self.state} score={self.score:.2f} batt={self.battery:.1f}%)")

