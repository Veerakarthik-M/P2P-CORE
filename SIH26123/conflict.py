# ============================================================
# conflict.py  —  Conflict Detection & Narrow-Lane Negotiation
#
# Per ideation doc Section 7:
#   1. Robots approaching the same narrow lane exchange P2P
#      messages declaring intent.
#   2. Both calculate Priority Score locally.
#   3. Higher score wins lane access; loser yields.
#   4. Explicit messages: NEGOTIATE → SCORE → GRANT/YIELD.
# ============================================================
from priority import choose_lane_owner, priority_score
from robot import WAITING, MOVING, NEGOTIATING, ENTERING_LANE, IN_LANE


class ConflictEvent:
    """Stores one recorded negotiation event for the dashboard/log."""
    def __init__(self, lane_id, sim_time, robots, winner_id, p2p_messages=None):
        self.lane_id   = lane_id
        self.sim_time  = sim_time
        self.robots    = {r.robot_id: {
            "priority": r.task_priority,
            "urgency" : r.urgency,
            "wait"    : round(r.wait_time, 1),
            "score"   : round(r.score, 2),
        } for r in robots}
        self.winner_id    = winner_id
        self.p2p_messages = p2p_messages or []  # list of negotiation message strings

    def __repr__(self):
        return f"ConflictEvent(lane={self.lane_id} winner={self.winner_id} t={self.sim_time:.1f}s)"


class ConflictManager:
    """
    Detects when 2+ robots are heading for the same narrow lane
    and runs the P2P negotiation to decide entry order.

    Per ideation doc: robots negotiate BEFORE entering, not after collision.
    """

    def __init__(self, warehouse):
        self.warehouse = warehouse
        # lane_id → robot_id currently inside the lane (or None)
        self.lane_owner: dict[int, str | None] = {
            i: None for i in range(len(warehouse.narrow_lanes))
        }
        self.event_log: list[ConflictEvent] = []
        self.latest_event: ConflictEvent | None = None

    # ----------------------------------------------------------
    def _next_cells(self, robot, n=5):
        """Return the next n cells in the robot's planned path."""
        start = robot.path_index + 1
        return robot.path[start: start + n]

    # ----------------------------------------------------------
    def _lane_in_path(self, robot):
        """Return (lane_id, lane_cell) if the next 5 steps hit a narrow lane."""
        for cell in self._next_cells(robot):
            lid = self.warehouse.get_narrow_lane_id(cell)
            if lid is not None:
                return lid, cell
        return None, None

    # ----------------------------------------------------------
    def resolve(self, robots: list, sim_time: float, msg_bus=None):
        """
        Main entry point — call once per simulation tick.
        Mutates robot.state and robot.wait_time as needed.

        If msg_bus is provided, logs explicit P2P negotiation messages
        so the dashboard shows R1→R2, R2→R1 communication.
        """
        # Build map: lane_id → list of robots approaching it
        # Exclude IDLE robots with no task — they should not contest lanes
        approaching: dict[int, list] = {}
        for robot in robots:
            if not robot.path or robot.state in (WAITING, NEGOTIATING):
                continue
            if robot.state == "IDLE" and robot.target is None:
                continue   # task done — not a lane contender
            lid, _ = self._lane_in_path(robot)
            if lid is not None:
                approaching.setdefault(lid, []).append(robot)

        for lid, contenders in approaching.items():
            # Release lane if:
            #   a) owner has physically moved through (no longer in narrow cell)
            #   b) owner finished its task (IDLE, no target) — it's just loitering
            #   c) owner is CHARGING at a station
            owner_id = self.lane_owner[lid]
            if owner_id is not None:
                owner_robot = next((r for r in robots if r.robot_id == owner_id), None)
                if (owner_robot is None
                        or not self.warehouse.is_narrow(owner_robot.position)
                        or (owner_robot.state == "IDLE" and owner_robot.target is None)
                        or owner_robot.state == "CHARGING"):
                    self.lane_owner[lid] = None
                    owner_id = None

            # Single robot approaching — just let it through
            if len(contenders) == 1:
                r = contenders[0]
                if owner_id is None:
                    self.lane_owner[lid] = r.robot_id
                    r.state = ENTERING_LANE
                else:
                    r.state = WAITING
                continue

            # ── MULTI-ROBOT NEGOTIATION ──────────────────────
            # Step 1: Each robot calculates its Priority Score
            for r in contenders:
                r.calculate_score()
                r.state = NEGOTIATING

            # Step 2: Exchange P2P intent messages
            p2p_msgs = []
            for r in contenders:
                for other in contenders:
                    if other.robot_id != r.robot_id:
                        detail = (
                            f"I intend to enter Lane #{lid}. "
                            f"My score={r.score:.2f} (P:{r.task_priority} U:{r.urgency} W:{r.wait_time:.1f}s)"
                        )
                        if msg_bus:
                            msg_bus.log_negotiation(
                                r.robot_id, other.robot_id,
                                "NEGOTIATE", sim_time, detail
                            )
                        p2p_msgs.append(f"{r.robot_id}→{other.robot_id}: {detail}")
                        # Log to robot's own event log
                        r.log_event(f"Sent NEGOTIATE to {other.robot_id}: score={r.score:.2f}", sim_time)

            if owner_id is None:
                # Step 3: Determine winner
                winner = choose_lane_owner(contenders)
                self.lane_owner[lid] = winner.robot_id
                winner.state = ENTERING_LANE

                # Step 4: Exchange GRANT / YIELD messages
                for r in contenders:
                    if r.robot_id == winner.robot_id:
                        # Winner sends GRANT to all losers
                        for other in contenders:
                            if other.robot_id != r.robot_id:
                                detail = (
                                    f"Lane #{lid} GRANTED to me. "
                                    f"score={r.score:.2f} > {other.score:.2f}. Proceed."
                                )
                                if msg_bus:
                                    msg_bus.log_negotiation(
                                        r.robot_id, other.robot_id,
                                        "GRANT", sim_time, detail
                                    )
                                p2p_msgs.append(f"{r.robot_id}→{other.robot_id}: GRANT - {detail}")
                        r.log_event(f"★ WON Lane #{lid} (score {r.score:.2f})", sim_time)
                    else:
                        # Loser sends YIELD acknowledgment
                        r.state       = WAITING
                        r.waiting_for = winner.robot_id
                        detail = (
                            f"Acknowledged. Yielding Lane #{lid} to {winner.robot_id}. "
                            f"My score={r.score:.2f} < {winner.score:.2f}. Waiting."
                        )
                        if msg_bus:
                            msg_bus.log_negotiation(
                                r.robot_id, winner.robot_id,
                                "YIELD", sim_time, detail
                            )
                        p2p_msgs.append(f"{r.robot_id}→{winner.robot_id}: YIELD - {detail}")
                        r.log_event(
                            f"Yielded Lane #{lid} to {winner.robot_id} "
                            f"(me:{r.score:.2f} < {winner.score:.2f})",
                            sim_time
                        )

                # Record the event with full P2P message trail
                evt = ConflictEvent(lid, sim_time, contenders, winner.robot_id, p2p_msgs)
                self.event_log.append(evt)
                self.latest_event = evt
            else:
                # Lane occupied — everyone waits
                for r in contenders:
                    r.state       = WAITING
                    r.waiting_for = owner_id
                    if msg_bus:
                        msg_bus.log_negotiation(
                            r.robot_id, owner_id,
                            "WAIT", sim_time,
                            f"Lane #{lid} occupied by {owner_id}. Waiting for clearance."
                        )

        # Release waiting robots whose blocker has cleared the lane
        from robot import CHARGING as CHARGING_STATE
        for robot in robots:
            if robot.state == WAITING and robot.waiting_for:
                blocker_still_in_lane = any(
                    self.lane_owner[lid] == robot.waiting_for
                    for lid in self.lane_owner
                )
                # Also release if blocker finished its task or is charging
                blocker_robot = next(
                    (r for r in robots if r.robot_id == robot.waiting_for), None
                )
                blocker_done = (
                    blocker_robot is None
                    or (blocker_robot.state == "IDLE" and blocker_robot.target is None)
                    or blocker_robot.state == CHARGING_STATE
                )
                if not blocker_still_in_lane or blocker_done:
                    robot.state       = MOVING
                    robot.log_event(f"Lane cleared by {robot.waiting_for}. Resuming.", sim_time)
                    robot.waiting_for = None
                    robot.calculate_score()

        # Update IN_LANE state
        for robot in robots:
            if robot.state == ENTERING_LANE:
                if self.warehouse.is_narrow(robot.position):
                    robot.state = IN_LANE
            elif robot.state == IN_LANE:
                if not self.warehouse.is_narrow(robot.position):
                    robot.state = MOVING
                    # Release lane ownership
                    for lid, owner in self.lane_owner.items():
                        if owner == robot.robot_id:
                            self.lane_owner[lid] = None
