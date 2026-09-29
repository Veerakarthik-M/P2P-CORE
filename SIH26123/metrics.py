# ============================================================
# metrics.py  —  Performance Metrics Recorder
# ============================================================
import csv
import os
import time


class MetricsTracker:
    def __init__(self):
        self.start_real_time   = time.time()
        self.start_sim_time    = 0.0

        self.total_collisions  = 0
        self.total_reroutes    = 0
        self.total_messages    = 0
        self.total_wait        = 0.0
        self.tasks_completed   = 0
        self.deadlock_events   = 0
        self.negotiation_events= 0
        self.max_wait_time     = 0.0

        # Per-robot snapshots
        self.robot_stats: dict[str, dict] = {}

        # Baseline comparison
        self.baseline_time: float | None = None  # stop-and-wait completion time
        self.our_time:      float | None = None  # our completion time

    # ----------------------------------------------------------
    def update(self, robots: list, sim_time: float):
        """Called every tick to refresh running totals."""
        self.total_collisions   = sum(r.collisions        for r in robots)
        self.total_reroutes     = sum(r.reroutes          for r in robots)
        self.total_messages     = sum(r.messages_sent     for r in robots)
        self.tasks_completed    = sum(r.tasks_completed   for r in robots)
        self.total_wait         = sum(r.total_wait        for r in robots)
        self.max_wait_time      = max(r.wait_time         for r in robots)

        for r in robots:
            self.robot_stats[r.robot_id] = {
                "state"    : r.state,
                "pos"      : r.position,
                "score"    : round(r.score, 2),
                "wait"     : round(r.wait_time, 2),
                "reroutes" : r.reroutes,
                "tasks"    : r.tasks_completed,
                "msgs"     : r.messages_sent,
            }

    # ----------------------------------------------------------
    def improvement_pct(self) -> float | None:
        """
        % improvement over stop-and-wait baseline.
        Returns None if baseline not yet recorded.
        """
        if self.baseline_time and self.our_time:
            diff = self.baseline_time - self.our_time
            return round(diff / self.baseline_time * 100, 1)
        return None

    # ----------------------------------------------------------
    def save_csv(self, robots: list, sim_time: float,
                 filepath: str = "results/simulation_results.csv"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        rows = []
        for r in robots:
            rows.append({
                "robot_id"          : r.robot_id,
                "tasks_completed"   : r.tasks_completed,
                "total_wait_s"      : round(r.total_wait, 2),
                "max_wait_s"        : round(r.wait_time, 2),
                "collisions"        : r.collisions,
                "reroutes"          : r.reroutes,
                "messages_sent"     : r.messages_sent,
            })
        summary = {
            "robot_id"          : "SUMMARY",
            "tasks_completed"   : self.tasks_completed,
            "total_wait_s"      : round(self.total_wait, 2),
            "max_wait_s"        : round(self.max_wait_time, 2),
            "collisions"        : self.total_collisions,
            "reroutes"          : self.total_reroutes,
            "messages_sent"     : self.total_messages,
        }
        rows.append(summary)
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"[Metrics] Saved to {filepath}")

    # ----------------------------------------------------------
    def summary_lines(self, sim_time: float) -> list[str]:
        """Short text lines for the dashboard panel."""
        imp = self.improvement_pct()
        imp_str = f"{imp:+.1f}%" if imp is not None else "N/A"
        return [
            f"Sim time     : {sim_time:.1f}s",
            f"Tasks done   : {self.tasks_completed}",
            f"Collisions   : {self.total_collisions}",
            f"Reroutes     : {self.total_reroutes}",
            f"Total wait   : {self.total_wait:.1f}s",
            f"Max wait     : {self.max_wait_time:.1f}s",
            f"Messages     : {self.total_messages}",
            f"Improvement  : {imp_str}",
        ]
