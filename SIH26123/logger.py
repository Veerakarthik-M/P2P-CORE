# ============================================================
# logger.py  —  Simulation Event Logger
# ============================================================
import os
import datetime


class SimLogger:
    def __init__(self, log_dir="results"):
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(log_dir, f"sim_log_{ts}.txt")
        self._lines   = []
        self.log(f"=== SIH26123 Simulation Log — {ts} ===")

    def log(self, msg: str):
        self._lines.append(msg)
        print(msg)

    def log_conflict(self, evt):
        self.log(
            f"[CONFLICT t={evt.sim_time:.1f}s] Lane={evt.lane_id} "
            f"Winner={evt.winner_id} "
            f"Scores={[(rid, d['score']) for rid, d in evt.robots.items()]}"
        )

    def log_reroute(self, robot_id, position):
        self.log(f"[REROUTE] {robot_id} at {position} replanned path")

    def log_task(self, robot_id, task_num):
        self.log(f"[TASK] {robot_id} completed task #{task_num}")

    def save(self):
        with open(self.filepath, "w") as f:
            f.write("\n".join(self._lines))
        print(f"[Logger] Log saved to {self.filepath}")
