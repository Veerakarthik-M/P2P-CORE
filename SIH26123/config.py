# ============================================================
# config.py  —  SIH26123 Central Configuration
# All tunable parameters live here. Change values here only.
# ============================================================

# --- Grid / Window ---
CELL_SIZE       = 32          # pixels per grid cell
COLS            = 28          # grid columns
ROWS            = 22          # grid rows
FPS             = 10          # simulation frames per second (speed)

# --- Priority Score Weights ---
ALPHA           = 0.5         # weight for task_priority
BETA            = 0.3         # weight for urgency
GAMMA           = 0.2         # weight for wait_time factor
WAIT_REFERENCE  = 30.0        # seconds after which W factor saturates at 5

# --- Simulation Timing ---
MSG_INTERVAL    = 1.0         # seconds between P2P broadcasts
ROBOT_SPEED     = 2           # cells moved per second (ticks × cell/tick)
MOVE_TICKS      = FPS // ROBOT_SPEED   # ticks between moves

# --- Robot Colors (R, G, B) ---
ROBOT_COLORS = {
    "R1": (52,  211, 153),   # teal-green
    "R2": (139, 92,  246),   # purple
    "R3": (251, 191, 36),    # amber
}

# --- Cell Colors ---
COLOR_BG        = (15,  17,  26)    # background
COLOR_WALL      = (40,  45,  60)    # rack / wall
COLOR_FLOOR     = (28,  32,  44)    # walkable
COLOR_START     = (30,  80,  60)    # robot start cell
COLOR_GOAL      = (80,  30,  60)    # delivery target cell
COLOR_OBSTACLE  = (200, 60,  60)    # dynamic obstacle
COLOR_NARROW    = (60,  90, 160)    # narrow-lane cell
COLOR_PATH      = (40,  60,  90)    # highlighted path
COLOR_GRID_LINE = (25,  29,  40)    # thin grid lines

# --- UI Panel ---
PANEL_W         = 410         # right-side dashboard width (pixels)
UI_FONT         = "Consolas"

# --- Scenario Defaults ---
N_ROBOTS        = 3
ROBOT_IDS       = ["R1", "R2", "R3"]

# --- Battery & Charging ---
# Initial battery per robot (percent 0-100)
BATTERY_INIT    = {"R1": 92, "R2": 78, "R3": 65}
# Battery drain while moving (percent per second)
BATTERY_DRAIN_MOVING  = 1.5
# Battery drain while idle/waiting (percent per second)
BATTERY_DRAIN_IDLE    = 0.1
# Thresholds
BATTERY_LOW           = 30    # percent — robot shows LOW warning
BATTERY_CRITICAL      = 15    # percent — robot heads to charger automatically
BATTERY_CHARGE_TARGET = 80    # percent — robot leaves charger at this level
# Charging rate (percent per second while docked at station)
BATTERY_CHARGE_RATE   = 5.0

# --- Charging Station Color ---
COLOR_CHARGER   = (255, 220, 50)   # bright yellow for charging station cells
