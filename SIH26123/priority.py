# ============================================================
# priority.py  —  Priority Score Calculation
# ============================================================
from config import ALPHA, BETA, GAMMA, WAIT_REFERENCE


def wait_factor(wait_seconds: float) -> float:
    """
    Normalize accumulated wait time to a 0-5 scale.
    W = min(wait_seconds / WAIT_REFERENCE, 5)
    """
    return min(wait_seconds / WAIT_REFERENCE, 5.0)


def priority_score(task_priority: int,
                   urgency: int,
                   wait_seconds: float) -> float:
    """
    Scoreᵢ = α·Pᵢ + β·Uᵢ + γ·Wᵢ

    Inputs (all expected on a 1–5 scale except wait_seconds):
      task_priority : int   1-5
      urgency       : int   1-5
      wait_seconds  : float accumulated wait in seconds

    Returns float score.
    """
    W = wait_factor(wait_seconds)
    return round(ALPHA * task_priority + BETA * urgency + GAMMA * W, 4)


def choose_lane_owner(robots: list) -> "Robot":
    """
    Given a list of Robot objects, return the one that should
    enter the narrow lane first.

    Tie-breaking rule: smallest robot_id string wins.
    """
    scored = [(priority_score(r.task_priority, r.urgency, r.wait_time), r.robot_id, r)
              for r in robots]
    # Sort descending by score, ascending by id on tie
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]   # winner Robot object
