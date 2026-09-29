# ============================================================
# warehouse.py  —  Grid Map & Narrow-Lane Registry
# ============================================================
import json
import os
from config import ROWS, COLS

# Cell type constants
WALL    = 0
FLOOR   = 1
NARROW  = 2   # narrow lane / choke point
CHARGE  = 3   # charging station cell

# ──────────────────────────────────────────────────────────────
# Default hardcoded map  (28 cols × 22 rows)
# 0 = wall/rack   1 = floor   2 = narrow lane (choke point)
# ──────────────────────────────────────────────────────────────
DEFAULT_MAP = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,1,1,1,1,1,0,1,1,2,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,1,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,1,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,0,0,1,1,0,1,0,0,0,1,0,1,0,0,1,1,0,1,0,0,0,0,1,0,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# Narrow lane cells (shared choke points robots compete for)
NARROW_LANES = [
    {(6, 9)},                    # top-center lane
    {(6, 21)},                   # top-right lane
    {(12, 9)},                   # mid-center lane
    {(12, 21)},                  # mid-right lane
]

# Robot start/goal pairs  [start(row,col), goal(row,col)]
ROBOT_CONFIGS = {
    "R1": {"start": (1, 1),  "goal": (20, 26)},
    "R2": {"start": (1, 26), "goal": (20, 1)},
    "R3": {"start": (20, 1), "goal": (1, 26)},
}

# Charging station definitions
# Each entry: {"id": "C1", "pos": (row, col)}
CHARGING_STATIONS = [
    {"id": "C1", "pos": (1, 3)},    # top-left area
    {"id": "C2", "pos": (20, 24)},  # bottom-right area
]

# Additional task goals for cycling tasks
TASK_POOL = [
    (1, 7), (1, 19), (1, 25),
    (5, 1), (5, 27),
    (10, 1),(10, 13),(10, 27),
    (17, 1),(17, 13),(17, 27),
    (20, 7),(20, 13),(20, 25),
]


class Warehouse:
    def __init__(self):
        self.grid             = [row[:] for row in DEFAULT_MAP]  # mutable copy
        # Mark charging station cells in the grid (CHARGE = 3, walkable)
        for cs in CHARGING_STATIONS:
            r, c = cs["pos"]
            self.grid[r][c] = CHARGE
        self.rows             = len(self.grid)
        self.cols             = len(self.grid[0])
        self.narrow_lanes     = NARROW_LANES          # list of sets
        self.dynamic_obstacles: set = set()           # temporarily blocked cells
        self.robot_configs    = ROBOT_CONFIGS
        self.charging_stations = CHARGING_STATIONS    # expose for rest of sim

    # ----------------------------------------------------------
    def is_walkable(self, r, c) -> bool:
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return False
        if self.grid[r][c] == WALL:
            return False
        if (r, c) in self.dynamic_obstacles:
            return False
        return True

    def get_grid_for_astar(self) -> list:
        """Return a 0/1 grid usable by A* (obstacles treated as 0)."""
        g = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                if (r, c) in self.dynamic_obstacles:
                    row.append(0)
                elif self.grid[r][c] == WALL:
                    row.append(0)
                else:
                    # FLOOR, NARROW, CHARGE are all walkable
                    row.append(1)
            g.append(row)
        return g

    # ----------------------------------------------------------
    def add_obstacle(self, r, c):
        self.dynamic_obstacles.add((r, c))

    def remove_obstacle(self, r, c):
        self.dynamic_obstacles.discard((r, c))

    def toggle_obstacle(self, r, c):
        if (r, c) in self.dynamic_obstacles:
            self.remove_obstacle(r, c)
        else:
            # Only place on floor cells
            if self.grid[r][c] != WALL:
                self.add_obstacle(r, c)

    # ----------------------------------------------------------
    def get_narrow_lane_id(self, cell: tuple):
        """Return which narrow-lane set this cell belongs to, or None."""
        for idx, lane_set in enumerate(self.narrow_lanes):
            if cell in lane_set:
                return idx
        return None

    def is_narrow(self, cell: tuple) -> bool:
        return any(cell in lane for lane in self.narrow_lanes)
