# ============================================================
# communication.py  —  Simulated P2P Message Bus
# Robots broadcast here; robots read from here.
# This IS NOT a central decision-maker — it only transports
# messages.  Decisions are made inside each Robot object.
# ============================================================
import time
import json


class MessageBus:
    """
    Simulated peer-to-peer communication layer.

    Every robot can:
      - broadcast(msg_dict)  → put its state in the shared bus
      - get_messages()       → read every other robot's last message

    The bus does NOT interpret or act on messages.

    Message types logged:
      STATE      — periodic 1s heartbeat (position, priority, wait)
      NEGOTIATE  — R1→R2 "I intend to enter lane X, my score is Y"
      YIELD      — R2→R1 "Acknowledged, I will yield lane X"
      REROUTE    — R1→ALL "Path blocked by R2 at (x,y), replanning"
    """

    def __init__(self):
        # {robot_id: latest_message_dict}
        self._inbox: dict[str, dict] = {}
        self._log:   list[str]       = []   # human-readable message log
        self._negotiation_log: list[str] = []  # dedicated negotiation messages

    # ----------------------------------------------------------
    def broadcast(self, robot_id: str, msg: dict):
        """Robot publishes its current state."""
        msg["robot_id"] = robot_id
        msg["timestamp"] = round(time.time(), 2)
        self._inbox[robot_id] = msg
        batt_str = f" batt={msg.get('battery', '?'):.1f}%" if isinstance(msg.get('battery'), (int, float)) else ""
        entry = (
            f"[{msg['sim_time']:.1f}s] {robot_id} → ALL : "
            f"pos={msg['position']} pri={msg['task_priority']} "
            f"wait={msg['wait_time']:.1f}s state={msg['state']}{batt_str}"
        )
        self._log.append(entry)
        if len(self._log) > 200:
            self._log.pop(0)

    # ----------------------------------------------------------
    def log_negotiation(self, sender: str, receiver: str,
                        msg_type: str, sim_time: float, detail: str):
        """
        Log a directed P2P negotiation message.

        msg_type: NEGOTIATE, YIELD, GRANT, REROUTE, DETECT
        """
        entry = f"[{sim_time:.1f}s] {sender} → {receiver} [{msg_type}] {detail}"
        self._negotiation_log.append(entry)
        self._log.append(entry)
        if len(self._negotiation_log) > 50:
            self._negotiation_log.pop(0)
        if len(self._log) > 200:
            self._log.pop(0)

    # ----------------------------------------------------------
    def get_messages(self, requester_id: str) -> list[dict]:
        """Return every robot's last message EXCEPT the requester's."""
        return [v for k, v in self._inbox.items() if k != requester_id]

    # ----------------------------------------------------------
    def get_all_messages(self) -> dict:
        """Return full inbox (used by dashboard)."""
        return dict(self._inbox)

    # ----------------------------------------------------------
    def get_log(self) -> list[str]:
        """Return last N log entries for display."""
        return self._log[-10:]

    # ----------------------------------------------------------
    def get_negotiation_log(self) -> list[str]:
        """Return all negotiation-specific entries (up to 50)."""
        return list(self._negotiation_log)   # caller slices what it needs

    # ----------------------------------------------------------
    def clear(self):
        self._inbox.clear()
        self._log.clear()
        self._negotiation_log.clear()


def build_message(robot, sim_time: float) -> dict:
    """
    Construct a standardised P2P message from a Robot object.

    Schema (from ideation doc Section 8):
    {
        "robot_id"      : "R1",
        "position"      : [row, col],
        "target"        : [row, col] or null,
        "task_priority" : 1-5,
        "urgency"       : 1-5,
        "wait_time"     : float (seconds),
        "ETA"           : float (seconds),
        "sim_time"      : float,
        "state"         : str,
        "next_cells"    : [[r,c], ...]
    }
    """
    next_cells = []
    if robot.path and robot.path_index < len(robot.path):
        start = robot.path_index + 1
        next_cells = [list(c) for c in robot.path[start:start + 3]]

    return {
        "robot_id"     : robot.robot_id,
        "position"     : list(robot.position),
        "target"       : list(robot.target) if robot.target else None,
        "task_priority": robot.task_priority,
        "urgency"      : robot.urgency,
        "wait_time"    : round(robot.wait_time, 2),
        "ETA"          : round(robot.eta(), 2),
        "sim_time"     : round(sim_time, 2),
        "state"        : robot.state,
        "next_cells"   : next_cells,
        "battery"      : round(robot.battery, 1),
    }
