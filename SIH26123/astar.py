# ============================================================
# astar.py  —  A* Path Planner
# Pure function — no state. Robots call this locally.
# ============================================================
import heapq


def heuristic(a, b):
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid, start, goal, reserved_cells=None):
    """
    A* on a 2-D grid.

    Parameters
    ----------
    grid          : list[list[int]]  1 = walkable, 0 = blocked
    start         : (row, col)
    goal          : (row, col)
    reserved_cells: set of (row, col) treated as temporarily blocked
                    (other robots' current positions, etc.)

    Returns
    -------
    list[(row, col)] — full path including start and goal,
                        or [] if no path exists.
    """
    if reserved_cells is None:
        reserved_cells = set()

    rows = len(grid)
    cols = len(grid[0])

    def walkable(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        if grid[r][c] == 0:
            return False
        if (r, c) in reserved_cells and (r, c) != goal:
            return False
        return True

    open_heap = []
    heapq.heappush(open_heap, (0 + heuristic(start, goal), 0, start))
    came_from = {start: None}
    g_score   = {start: 0}

    while open_heap:
        _, g, current = heapq.heappop(open_heap)

        if current == goal:
            # Reconstruct path
            path = []
            node = goal
            while node is not None:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path

        if g > g_score.get(current, float('inf')):
            continue   # stale entry

        r, c = current
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nb = (r + dr, c + dc)
            if not walkable(*nb):
                continue
            ng = g + 1
            if ng < g_score.get(nb, float('inf')):
                g_score[nb] = ng
                came_from[nb] = current
                f = ng + heuristic(nb, goal)
                heapq.heappush(open_heap, (f, ng, nb))

    return []   # no path found
