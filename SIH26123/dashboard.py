# ============================================================
# dashboard.py  —  Pygame Visual Dashboard
# Renders: warehouse grid, robots, paths, messages, metrics,
# and 5-Tab Navigation Panel (FLEET | R1 | R2 | R3 | CONFLICT)
# ============================================================
import pygame
from config import (CELL_SIZE, PANEL_W, ROWS, COLS, FPS,
                    COLOR_BG, COLOR_WALL, COLOR_FLOOR, COLOR_NARROW,
                    COLOR_OBSTACLE, COLOR_GRID_LINE, COLOR_PATH,
                    COLOR_START, COLOR_GOAL, ROBOT_COLORS, UI_FONT,
                    COLOR_CHARGER, BATTERY_LOW, BATTERY_CRITICAL)
from warehouse import WALL, FLOOR, NARROW, CHARGE
from robot import (IDLE, MOVING, WAITING, NEGOTIATING,
                   APPROACHING_CONFLICT, ENTERING_LANE, IN_LANE,
                   DELIVERING, COMPLETED, CHARGING, STALLED)

# State → color tint
STATE_COLORS = {
    IDLE                : (100, 100, 120),
    MOVING              : (52,  211, 153),
    WAITING             : (251, 100, 100),
    NEGOTIATING         : (251, 191, 36),
    APPROACHING_CONFLICT: (255, 165, 0),
    ENTERING_LANE       : (100, 200, 255),
    IN_LANE             : (60,  150, 255),
    DELIVERING          : (180, 255, 140),
    COMPLETED           : (150, 150, 150),
    CHARGING            : (255, 220,  50),   # bright yellow while charging
    STALLED             : (255,  60,  60),   # bright red — stuck, needs attention
}

GRID_W = COLS * CELL_SIZE
GRID_H = ROWS * CELL_SIZE
WIN_W  = GRID_W + PANEL_W
WIN_H  = GRID_H

TABS = ["FLEET", "R1", "R2", "R3", "CONFLICT"]


class Dashboard:
    def __init__(self, warehouse, scenario_name="Normal"):
        pygame.init()
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption(f"SIH26123 – AMR Fleet Simulation  [{scenario_name}]")
        self.clock   = pygame.time.Clock()
        self.warehouse = warehouse

        # Fonts
        self.font_sm  = pygame.font.SysFont(UI_FONT, 13)
        self.font_md  = pygame.font.SysFont(UI_FONT, 15, bold=True)
        self.font_lg  = pygame.font.SysFont(UI_FONT, 18, bold=True)
        self.font_hd  = pygame.font.SysFont(UI_FONT, 20, bold=True)

        self.scenario_name = scenario_name
        self.active_tab    = "FLEET"

    # ── TAB INTERACTION ────────────────────────────────────────
    def handle_click(self, mx, my):
        """Switch active tab if mouse clicked on tab bar."""
        px = GRID_W
        if px + 10 <= mx <= px + PANEL_W - 10 and 60 <= my <= 86:
            rel_x = mx - (px + 10)
            tab_w = (PANEL_W - 20) // len(TABS)
            idx   = rel_x // tab_w
            if 0 <= idx < len(TABS):
                self.active_tab = TABS[idx]

    def cycle_tab(self):
        """Cycle to next tab using TAB key."""
        idx = (TABS.index(self.active_tab) + 1) % len(TABS)
        self.active_tab = TABS[idx]

    # ── MAIN DRAW CALL ─────────────────────────────────────────
    def draw(self, robots, metrics, msg_bus, conflict_mgr,
             sim_time, paused, ctrl_room_online,
             charger_occupancy=None):
        self.screen.fill(COLOR_BG)
        self._draw_grid()
        self._draw_obstacles()
        self._draw_paths(robots)
        self._draw_narrow_lanes()
        self._draw_charging_stations(charger_occupancy or {})
        self._draw_robots(robots)
        self._draw_goals(robots)
        self._draw_panel(robots, metrics, msg_bus, conflict_mgr,
                         sim_time, paused, ctrl_room_online,
                         charger_occupancy or {})
        pygame.display.flip()
        self.clock.tick(FPS)

    # ── GRID ───────────────────────────────────────────────────
    def _draw_grid(self):
        wh = self.warehouse
        for r in range(wh.rows):
            for c in range(wh.cols):
                x = c * CELL_SIZE
                y = r * CELL_SIZE
                cell_val = wh.grid[r][c]
                if cell_val == WALL:
                    color = COLOR_WALL
                elif cell_val == NARROW:
                    color = COLOR_NARROW
                else:
                    color = COLOR_FLOOR
                pygame.draw.rect(self.screen, color, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, COLOR_GRID_LINE,
                                 (x, y, CELL_SIZE, CELL_SIZE), 1)

    def _draw_narrow_lanes(self):
        """Highlight narrow-lane cells with a blue tint."""
        for lane_set in self.warehouse.narrow_lanes:
            for (r, c) in lane_set:
                x = c * CELL_SIZE
                y = r * CELL_SIZE
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                s.fill((80, 130, 255, 100))
                self.screen.blit(s, (x, y))
                lbl = self.font_sm.render("N", True, (160, 200, 255))
                self.screen.blit(lbl, (x + 9, y + 8))

    def _draw_charging_stations(self, charger_occupancy):
        """Draw charging stations on the grid with a battery icon."""
        for cs in self.warehouse.charging_stations:
            r, c = cs["pos"]
            cid  = cs["id"]
            x = c * CELL_SIZE
            y = r * CELL_SIZE
            occupant = charger_occupancy.get(cid)
            col = (255, 150, 30) if occupant else COLOR_CHARGER
            # Filled square
            pygame.draw.rect(self.screen, col,
                             (x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4),
                             border_radius=3)
            # Label
            lbl = self.font_sm.render(cid, True, (20, 20, 20))
            self.screen.blit(lbl, (x + 2, y + 2))
            # Show occupant
            if occupant:
                occ_lbl = self.font_sm.render(occupant, True, (60, 20, 20))
                self.screen.blit(occ_lbl, (x + 2, y + 14))

    def _draw_obstacles(self):
        for (r, c) in self.warehouse.dynamic_obstacles:
            x = c * CELL_SIZE
            y = r * CELL_SIZE
            pygame.draw.rect(self.screen, COLOR_OBSTACLE,
                             (x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4))
            lbl = self.font_sm.render("X", True, (255, 255, 255))
            self.screen.blit(lbl, (x + 9, y + 8))

    # ── PATHS ──────────────────────────────────────────────────
    def _draw_paths(self, robots):
        for robot in robots:
            if not robot.path:
                continue

            # If in Robot detail view, highlight only that robot's path brightly
            if self.active_tab in ("R1", "R2", "R3"):
                if robot.robot_id != self.active_tab:
                    continue
                color  = ROBOT_COLORS.get(robot.robot_id, (200, 200, 200))
                line_w = 4
            else:
                color  = ROBOT_COLORS.get(robot.robot_id, (200, 200, 200))
                line_w = 2

            for idx in range(robot.path_index, len(robot.path) - 1):
                r1, c1 = robot.path[idx]
                r2, c2 = robot.path[idx + 1]
                x1 = c1 * CELL_SIZE + CELL_SIZE // 2
                y1 = r1 * CELL_SIZE + CELL_SIZE // 2
                x2 = c2 * CELL_SIZE + CELL_SIZE // 2
                y2 = r2 * CELL_SIZE + CELL_SIZE // 2
                pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), line_w)

    # ── ROBOTS ─────────────────────────────────────────────────
    def _draw_robots(self, robots):
        for robot in robots:
            r, c = robot.position
            x = c * CELL_SIZE + CELL_SIZE // 2
            y = r * CELL_SIZE + CELL_SIZE // 2
            color  = ROBOT_COLORS.get(robot.robot_id, (200, 200, 200))
            radius = CELL_SIZE // 2 - 3

            # State ring
            state_col = STATE_COLORS.get(robot.display_state, (200, 200, 200))
            pygame.draw.circle(self.screen, state_col, (x, y), radius + 3)
            pygame.draw.circle(self.screen, color, (x, y), radius)

            # Robot ID label
            lbl = self.font_md.render(robot.robot_id, True, (10, 10, 20))
            self.screen.blit(lbl, (x - lbl.get_width() // 2,
                                   y - lbl.get_height() // 2))

            # Score badge (above robot)
            sc_txt = self.font_sm.render(f"{robot.score:.2f}", True, (240, 240, 240))
            self.screen.blit(sc_txt, (x - sc_txt.get_width() // 2, y - radius - 16))

    # ── GOALS ──────────────────────────────────────────────────
    def _draw_goals(self, robots):
        for robot in robots:
            if robot.target is None:
                continue
            r, c = robot.target
            x = c * CELL_SIZE
            y = r * CELL_SIZE
            color = ROBOT_COLORS.get(robot.robot_id, (200, 200, 200))
            pygame.draw.rect(self.screen, color,
                             (x + 4, y + 4, CELL_SIZE - 8, CELL_SIZE - 8), 2)
            lbl = self.font_sm.render("G", True, color)
            self.screen.blit(lbl, (x + 9, y + 8))

    # ── RIGHT PANEL ────────────────────────────────────────────
    def _draw_panel(self, robots, metrics, msg_bus, conflict_mgr,
                    sim_time, paused, ctrl_room_online, charger_occupancy=None):
        charger_occupancy = charger_occupancy or {}
        px = GRID_W   # panel x-start
        py = 0

        # Background
        pygame.draw.rect(self.screen, (20, 22, 35), (px, py, PANEL_W, WIN_H))
        pygame.draw.line(self.screen, (50, 55, 80), (px, 0), (px, WIN_H), 2)

        y = 10
        # ── Header
        self._panel_text("SMART WAREHOUSE — SIH26123", px + 10, y,
                         self.font_hd, (100, 200, 255))
        y += 24
        scenario_col = (80, 200, 80) if not paused else (200, 150, 50)
        status_str = "⏸ PAUSED" if paused else f"▶ {self.scenario_name}"
        self._panel_text(status_str, px + 10, y, self.font_md, scenario_col)

        ctrl_col = (80, 200, 80) if ctrl_room_online else (200, 80, 80)
        ctrl_str = "CTRL ROOM: ONLINE" if ctrl_room_online else "CTRL ROOM: OFFLINE"
        self._panel_text(ctrl_str, px + PANEL_W - 160, y, self.font_sm, ctrl_col)
        y += 26

        # ── TAB BAR ────────────────────────────────────────────
        self._draw_tab_bar(px, y)
        y += 34

        # ── TAB CONTENT ────────────────────────────────────────
        if self.active_tab == "FLEET":
            self._draw_panel_fleet(px, y, robots, metrics, msg_bus, conflict_mgr,
                                   sim_time, ctrl_room_online, charger_occupancy)
        elif self.active_tab in ("R1", "R2", "R3"):
            self._draw_panel_robot(px, y, self.active_tab, robots, msg_bus)
        elif self.active_tab == "CONFLICT":
            self._draw_panel_conflict(px, y, conflict_mgr, msg_bus)

        # ── Footer Controls Hint
        y_foot = WIN_H - 22
        self._panel_text(
            "[TAB/Click] View  [1-7] Scenario  [SPACE] Pause  [C] Ctrl  [R] Reset",
            px + 8, y_foot, self.font_sm, (90, 110, 140))

    def _draw_tab_bar(self, px, y):
        tab_w = (PANEL_W - 20) // len(TABS)
        for i, tab_name in enumerate(TABS):
            tx = px + 10 + i * tab_w
            ty = y
            is_active = (self.active_tab == tab_name)

            if is_active:
                bg_col  = (40, 70, 120)
                brd_col = (100, 200, 255)
                txt_col = (255, 255, 255)
            else:
                bg_col  = (25, 30, 45)
                brd_col = (50, 60, 80)
                txt_col = (140, 150, 180)

            pygame.draw.rect(self.screen, bg_col, (tx, ty, tab_w - 4, 26), border_radius=4)
            pygame.draw.rect(self.screen, brd_col, (tx, ty, tab_w - 4, 26), 1, border_radius=4)

            lbl = self.font_sm.render(tab_name, True, txt_col)
            lx = tx + (tab_w - 4 - lbl.get_width()) // 2
            ly = ty + 5
            self.screen.blit(lbl, (lx, ly))

    # ── TAB 1: FLEET VIEW ──────────────────────────────────────
    def _draw_panel_fleet(self, px, y, robots, metrics, msg_bus, conflict_mgr,
                          sim_time, ctrl_room_online, charger_occupancy=None):
        charger_occupancy = charger_occupancy or {}
        # ROBOTS summary with battery bars
        self._divider(px, y, "FLEET SUMMARY"); y += 22
        for robot in robots:
            color     = ROBOT_COLORS.get(robot.robot_id, (200, 200, 200))
            state_col = STATE_COLORS.get(robot.display_state, (200, 200, 200))

            # Robot ID + state
            self._panel_text(f"● {robot.robot_id}", px + 10, y, self.font_md, color)
            stall_tag = "  ⚠ STALLED" if robot.display_state == STALLED else ""
            self._panel_text(robot.display_state + stall_tag, px + 55, y, self.font_md, state_col)
            y += 16

            # Pos / Score / Wait
            self._panel_text(
                f"  Pos:{robot.position}  Score:{robot.score:.2f}  Wait:{robot.wait_time:.1f}s",
                px + 10, y, self.font_sm, (180, 180, 200))
            y += 15

            # Battery bar
            pct = max(0.0, min(robot.battery, 100.0))
            bar_w = PANEL_W - 28
            filled = int(bar_w * pct / 100)
            if pct > BATTERY_LOW:
                bar_col = (60, 200, 80)    # green
            elif pct > BATTERY_CRITICAL:
                bar_col = (255, 165, 0)    # orange
            else:
                bar_col = (220, 50, 50)    # red
            pygame.draw.rect(self.screen, (40, 45, 60),
                             (px + 14, y, bar_w, 9), border_radius=3)
            if filled > 0:
                pygame.draw.rect(self.screen, bar_col,
                                 (px + 14, y, filled, 9), border_radius=3)
            batt_label = f"{pct:.0f}%"
            if robot.state == CHARGING:
                batt_label += " ⚡ CHARGING"
            elif robot.battery_status != "NORMAL":
                batt_label += f" ({robot.battery_status})"
            self._panel_text(batt_label, px + 14 + bar_w + 4, y - 1,
                             self.font_sm, bar_col)
            y += 14

        # CONFLICT section
        y += 4
        self._divider(px, y, "LATEST CONFLICT"); y += 22
        evt = conflict_mgr.latest_event
        if evt:
            self._panel_text(f"Lane #{evt.lane_id}  t={evt.sim_time:.1f}s",
                             px + 10, y, self.font_md, (251, 191, 36))
            y += 18
            for rid, data in evt.robots.items():
                win_marker = "★ WINNER" if rid == evt.winner_id else "  WAIT"
                w_col = (80, 220, 120) if rid == evt.winner_id else (220, 100, 100)
                self._panel_text(
                    f"  {rid}: pri={data['priority']} urg={data['urgency']} "
                    f"score={data['score']:.2f} {win_marker}",
                    px + 10, y, self.font_sm, w_col)
                y += 16
        else:
            self._panel_text("No conflict recorded yet.", px + 10, y,
                             self.font_sm, (110, 120, 140))
            y += 16

        # P2P MESSAGES section
        y += 4
        self._divider(px, y, "P2P COMMUNICATION LOG"); y += 22
        for line in msg_bus.get_log():
            # Color negotiation messages differently
            if "[NEGOTIATE]" in line or "[GRANT]" in line or "[YIELD]" in line:
                col = (251, 191, 36)
            elif "[DETECT]" in line or "[REROUTE]" in line:
                col = (251, 130, 100)
            elif "[CTRL_ROOM]" in line:
                col = (200, 80, 80) if "OFFLINE" in line else (80, 200, 80)
            else:
                col = (140, 180, 220)
            self._panel_text(line, px + 8, y, self.font_sm, col)
            y += 15
            if y > WIN_H - 180:
                break

        # CONTROL ROOM STATUS
        y = WIN_H - 215
        self._divider(px, y, "CONTROL ROOM STATUS"); y += 22
        if ctrl_room_online:
            self._panel_text("● ONLINE — Dashboard monitoring active",
                             px + 10, y, self.font_sm, (80, 200, 80))
        else:
            self._panel_text("● OFFLINE — Robots operating in Edge-AI P2P mode",
                             px + 10, y, self.font_sm, (200, 80, 80))
            y += 16
            self._panel_text("  (Robots still coordinate via direct P2P)",
                             px + 10, y, self.font_sm, (180, 150, 100))
        y += 18

        # CHARGING STATION STATUS
        self._divider(px, y, "CHARGING STATIONS"); y += 20
        for cs in self.warehouse.charging_stations:
            cid = cs["id"]
            occupant = charger_occupancy.get(cid)
            if occupant:
                occ_col = (251, 160, 40)
                status_str = f"● {cid}: OCCUPIED — {occupant}"
            else:
                occ_col = (60, 200, 100)
                status_str = f"○ {cid}: AVAILABLE"
            self._panel_text(status_str, px + 10, y, self.font_sm, occ_col)
            y += 16
        y += 4

        # METRICS section at bottom
        self._divider(px, y, "FLEET METRICS"); y += 22
        for line in metrics.summary_lines(sim_time):
            self._panel_text(line, px + 10, y, self.font_sm, (180, 220, 180))
            y += 16

    # ── TAB 2-4: INDIVIDUAL ROBOT VIEW ────────────────────────
    def _draw_panel_robot(self, px, y, robot_id, robots, msg_bus):
        robot = next((r for r in robots if r.robot_id == robot_id), None)
        if not robot:
            return

        r_color   = ROBOT_COLORS.get(robot_id, (200, 200, 200))
        state_col = STATE_COLORS.get(robot.display_state, (200, 200, 200))

        # Header card
        self._panel_text(f"ROBOT {robot_id} DETAILS", px + 10, y, self.font_hd, r_color)
        y += 24

        # Status & Location
        self._divider(px, y, "STATUS & NAVIGATION"); y += 22
        self._panel_text("State:", px + 10, y, self.font_sm, (160, 170, 190))
        self._panel_text(robot.display_state, px + 75, y, self.font_md, state_col)
        y += 18
        self._panel_text(f"Position: {robot.position}", px + 10, y, self.font_sm, (220, 220, 240))
        y += 16
        tgt_str = f"{robot.target}" if robot.target else "None"
        self._panel_text(f"Target:   {tgt_str}", px + 10, y, self.font_sm, (220, 220, 240))
        y += 16
        self._panel_text(f"ETA: {robot.eta():.1f}s | Tasks Done: {robot.tasks_completed}",
                         px + 10, y, self.font_sm, (180, 200, 180))
        y += 22

        # Priority Score Calculation Breakdown
        self._divider(px, y, "PRIORITY SCORE BREAKDOWN"); y += 22
        self._panel_text("Score = 0.5*P + 0.3*U + 0.2*min(W/30,1)*5", px + 10, y, self.font_sm, (120, 140, 170))
        y += 16
        p_val = 0.5 * robot.task_priority
        u_val = 0.3 * robot.urgency
        w_factor = min(robot.wait_time / 30.0, 1.0) * 5.0
        w_val = 0.2 * w_factor
        self._panel_text(f"P={robot.task_priority} [0.5x{robot.task_priority}={p_val:.2f}]", px + 10, y, self.font_sm, (200, 200, 220))
        y += 16
        self._panel_text(f"U={robot.urgency} [0.3x{robot.urgency}={u_val:.2f}]", px + 10, y, self.font_sm, (200, 200, 220))
        y += 16
        self._panel_text(f"W={robot.wait_time:.1f}s [0.2x{w_factor:.2f}={w_val:.2f}]", px + 10, y, self.font_sm, (200, 200, 220))
        y += 18
        self._panel_text(f"TOTAL SCORE: {robot.score:.2f}", px + 10, y, self.font_md, (251, 191, 36))
        y += 24

        # Path Progress Bar
        self._divider(px, y, "PATH PROGRESS"); y += 22
        total_steps = len(robot.path)
        current_step= robot.path_index
        pct = (current_step / total_steps) * 100 if total_steps > 0 else 0
        self._panel_text(f"Step {current_step}/{total_steps} ({pct:.0f}%)", px + 10, y, self.font_sm, (180, 200, 220))
        y += 16
        # Progress bar rect
        bar_w = PANEL_W - 30
        pygame.draw.rect(self.screen, (40, 45, 60), (px + 10, y, bar_w, 12), border_radius=3)
        if total_steps > 0:
            fill_w = int(bar_w * (current_step / total_steps))
            pygame.draw.rect(self.screen, r_color, (px + 10, y, fill_w, 12), border_radius=3)
        y += 20

        # Communication Stats
        self._divider(px, y, "P2P COMMUNICATION"); y += 22
        self._panel_text(f"Messages Sent    : {robot.messages_sent}", px + 10, y, self.font_sm, (160, 200, 240))
        y += 16
        self._panel_text(f"Messages Received: {robot.messages_recv}", px + 10, y, self.font_sm, (160, 200, 240))
        y += 16
        self._panel_text(f"Total Reroutes   : {robot.reroutes}", px + 10, y, self.font_sm, (160, 200, 240))
        y += 22

        # Battery Section
        self._divider(px, y, "BATTERY"); y += 20
        batt_pct = robot.battery
        if batt_pct >= BATTERY_LOW:
            batt_col = (60, 200, 100)
        elif batt_pct >= BATTERY_CRITICAL:
            batt_col = (251, 160, 40)
        else:
            batt_col = (220, 60, 60)
        self._panel_text(f"{batt_pct:.1f}%", px + 10, y, self.font_lg, batt_col)
        y += 22
        bar_w = PANEL_W - 30
        pygame.draw.rect(self.screen, (35, 40, 55), (px + 10, y, bar_w, 14), border_radius=3)
        fill_w = int(bar_w * batt_pct / 100)
        pygame.draw.rect(self.screen, batt_col, (px + 10, y, fill_w, 14), border_radius=3)
        y += 18
        if robot.state == CHARGING:
            status_str = f"Status: CHARGING @ {robot.charging_station_id}"
            if robot._pre_charge_target:
                self._panel_text(f"Resume Target: {robot._pre_charge_target}",
                                 px + 10, y + 16, self.font_sm, (180, 200, 220))
        else:
            status_str = f"Status: {robot.battery_status}"
        self._panel_text(status_str, px + 10, y, self.font_sm, batt_col)
        if robot._pre_charge_target:
            self._panel_text(f"Previous Task: {robot._pre_charge_target}",
                             px + 10, y + 16, self.font_sm, (140, 170, 200))
        y += 36

        # Event Log (shows actual sim_time timestamps now)
        self._divider(px, y, "DECISION LOG"); y += 22
        if robot.event_log:
            for entry in reversed(robot.event_log[-8:]):
                # Color based on event type
                if "WON" in entry or "✓" in entry:
                    col = (80, 220, 120)
                elif "Yielded" in entry or "Blocked" in entry:
                    col = (251, 130, 100)
                elif "NEGOTIATE" in entry or "Sent" in entry:
                    col = (251, 191, 36)
                elif "task" in entry.lower() or "→" in entry:
                    col = (100, 200, 255)
                else:
                    col = (150, 180, 210)
                self._panel_text(entry, px + 8, y, self.font_sm, col)
                y += 15
                if y > WIN_H - 40:
                    break
        else:
            self._panel_text("No events logged yet.", px + 10, y, self.font_sm, (110, 120, 140))

    # ── TAB 5: CONFLICT VIEW ────────────────────────────────────
    def _draw_panel_conflict(self, px, y, conflict_mgr, msg_bus):
        self._panel_text("CONFLICT ANALYSIS", px + 10, y, self.font_hd, (251, 191, 36))
        y += 26

        # ── P2P NEGOTIATION LOG first (always visible regardless of event size)
        self._divider(px, y, "P2P NEGOTIATION LOG"); y += 20
        neg_log = msg_bus.get_negotiation_log()
        MAX_NEG_Y = y + 8 * 15 + 10   # reserve space for up to 8 entries
        if neg_log:
            for entry in reversed(neg_log[-8:]):
                display = entry if len(entry) < 64 else entry[:61] + "..."
                if "[PRIORITY]" in entry or "[GRANT]" in entry:
                    col = (80, 220, 120)
                elif "[YIELD]" in entry:
                    col = (220, 130, 100)
                elif "[BATT_LOW]" in entry or "[CHARGING]" in entry:
                    col = (255, 220, 50)
                elif "[CHARGED]" in entry:
                    col = (100, 255, 180)
                elif "[DETECT]" in entry or "[REROUTE]" in entry:
                    col = (251, 130, 100)
                elif "[CTRL_ROOM]" in entry:
                    col = (200, 80, 80) if "OFFLINE" in entry else (80, 200, 80)
                else:
                    col = (140, 180, 220)
                self._panel_text(display, px + 8, y, self.font_sm, col)
                y += 15
        else:
            self._panel_text("No P2P messages yet.", px + 8, y, self.font_sm, (110, 120, 140))
            y += 15
        y = max(y, MAX_NEG_Y)   # guarantee we don't overlap next section

        # ── LATEST NARROW-LANE NEGOTIATION (below P2P log)
        y += 6
        self._divider(px, y, "LATEST LANE NEGOTIATION"); y += 20
        evt = conflict_mgr.latest_event
        if evt:
            self._panel_text(f"Lane #{evt.lane_id} at t={evt.sim_time:.1f}s", px + 10, y, self.font_md, (100, 200, 255))
            y += 18
            for rid, data in evt.robots.items():
                is_win = (rid == evt.winner_id)
                res_col = (80, 220, 120) if is_win else (220, 100, 100)
                res_str = "WINNER" if is_win else "YIELD"
                self._panel_text(
                    f"  {rid}: score={data['score']:.2f}  {res_str}",
                    px + 10, y, self.font_sm, res_col)
                y += 14
            y += 4
            # Decision Rationale (compact)
            win_data = evt.robots.get(evt.winner_id, {})
            losers = [rid for rid in evt.robots if rid != evt.winner_id]
            self._panel_text(
                f"Winner: {evt.winner_id} ({win_data.get('score',0):.2f}) > " +
                ", ".join(f"{l} ({evt.robots[l]['score']:.2f})" for l in losers),
                px + 10, y, self.font_sm, (200, 200, 220))
            y += 16
        else:
            self._panel_text("No lane conflict yet. Press [2] or [4].",
                             px + 10, y, self.font_sm, (140, 150, 170))
            y += 16

        # ── LANE CONFLICT HISTORY
        y += 4
        self._divider(px, y, "LANE CONFLICT HISTORY"); y += 20
        if conflict_mgr.event_log:
            for log_evt in reversed(conflict_mgr.event_log[-4:]):
                cont_str = ", ".join(log_evt.robots.keys())
                self._panel_text(
                    f"[{log_evt.sim_time:.1f}s] Lane#{log_evt.lane_id}: "
                    f"{log_evt.winner_id} won vs ({cont_str})",
                    px + 8, y, self.font_sm, (150, 190, 230))
                y += 14
                if y > WIN_H - 30:
                    break
        else:
            self._panel_text("History is empty.", px + 8, y, self.font_sm, (110, 120, 140))

    # ── HELPERS ────────────────────────────────────────────────
    def _panel_text(self, text, x, y, font, color):
        surf = font.render(str(text), True, color)
        self.screen.blit(surf, (x, y))

    def _divider(self, px, y, label):
        pygame.draw.line(self.screen, (50, 55, 80),
                         (px + 6, y + 8), (px + PANEL_W - 10, y + 8), 1)
        lbl = self.font_sm.render(f"  {label}  ", True, (80, 100, 150))
        self.screen.blit(lbl, (px + 15, y))

    def tick(self):
        self.clock.tick(FPS)

    def quit(self):
        pygame.quit()
