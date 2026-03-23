"""SpatialModel: Learn player shape, step size, wall colors from observation.

General-purpose spatial model that auto-learns game layout from frame diffs.
Works for any ARC game with a controllable player entity.

State machine:
  learning  →  enabled   (after 3 consistent player detections)
  learning  →  disabled  (after 10 moves with no consistent player)
  enabled   →  learning  (if player template not found 3 times in a row)
"""
from __future__ import annotations

import logging
from collections import Counter
from statistics import median
from typing import Optional

logger = logging.getLogger(__name__)


class SpatialModel:
    """Auto-learns player shape, movement, and wall colors from grid diffs."""

    def __init__(self) -> None:
        self.state: str = "learning"  # "learning" | "enabled" | "disabled"

        # Player template: set of (rel_row, rel_col, color) offsets from top-left
        self.player_template: Optional[frozenset[tuple[int, int, int]]] = None
        self.player_colors: set[int] = set()
        self.player_position: Optional[tuple[int, int]] = None  # (row, col) top-left

        # Movement learning
        self.action_displacements: dict[str, list[tuple[int, int]]] = {}  # raw obs
        self.confirmed_displacements: dict[str, tuple[int, int]] = {}  # locked in

        # Wall learning
        self.wall_color_evidence: Counter = Counter()
        self.confirmed_walls: frozenset[int] = frozenset()
        self.traversed_colors: set[int] = set()

        # Internal counters
        self._template_observations: list[frozenset[tuple[int, int, int]]] = []
        self._move_count: int = 0
        self._find_failures: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def learn_from_move(
        self,
        action: str,
        prev_grid: list[list[int]],
        curr_grid: list[list[int]],
        noise_rows: set[int],
    ) -> None:
        """Called on meaningful_change: learn player shape + displacement."""
        self._move_count += 1
        if self.state == "disabled":
            return

        rows = len(prev_grid)
        cols = len(prev_grid[0]) if rows else 0
        bg = self._background_color(prev_grid)

        # Diff grids excluding noise rows
        vacated: set[tuple[int, int, int]] = set()   # (r, c, color) — cells that disappeared
        appeared: set[tuple[int, int, int]] = set()   # (r, c, color) — cells that appeared

        for r in range(rows):
            if r in noise_rows:
                continue
            for c in range(cols):
                old, new = prev_grid[r][c], curr_grid[r][c]
                if old != new:
                    # Filter out background transitions
                    if old != bg:
                        vacated.add((r, c, old))
                    if new != bg:
                        appeared.add((r, c, new))

        if not vacated or not appeared:
            self._check_disable()
            return

        # Compute displacement from centroids
        vac_rows = [r for r, _, _ in vacated]
        vac_cols = [c for _, c, _ in vacated]
        app_rows = [r for r, _, _ in appeared]
        app_cols = [c for _, c, _ in appeared]

        dr = round(sum(app_rows) / len(app_rows) - sum(vac_rows) / len(vac_rows))
        dc = round(sum(app_cols) / len(app_cols) - sum(vac_cols) / len(vac_cols))

        if dr == 0 and dc == 0:
            self._check_disable()
            return

        # Shift appeared back to check template overlap with vacated
        shifted_back: set[tuple[int, int, int]] = {
            (r - dr, c - dc, color) for r, c, color in appeared
        }
        overlap = shifted_back & vacated
        overlap_ratio = len(overlap) / max(len(vacated), 1)

        if overlap_ratio >= 0.6:
            # Good template observation — use vacated set as template
            # Normalize to top-left = (0, 0)
            min_r = min(r for r, _, _ in vacated)
            min_c = min(c for _, c, _ in vacated)
            template = frozenset(
                (r - min_r, c - min_c, color) for r, c, color in vacated
            )
            self._template_observations.append(template)

            # Record displacement
            self.action_displacements.setdefault(action, []).append((dr, dc))

            # Update player position from appeared set (new position)
            new_min_r = min(r for r, _, _ in appeared)
            new_min_c = min(c for _, c, _ in appeared)
            self.player_position = (new_min_r, new_min_c)

            # Track colors we've traversed through (in the target area)
            for r, c, color in appeared:
                if color not in {clr for _, _, clr in template}:
                    self.traversed_colors.add(color)

            # Check if we have enough consistent observations to enable
            if self.state == "learning" and len(self._template_observations) >= 3:
                self._try_enable()
            elif self.state == "enabled":
                # Update confirmed displacement for this action
                self.confirmed_displacements[action] = (
                    int(median(d[0] for d in self.action_displacements[action])),
                    int(median(d[1] for d in self.action_displacements[action])),
                )
        else:
            self._check_disable()

        # Reset find_failures on successful move
        self._find_failures = 0

    def learn_from_block(self, action: str, curr_grid: list[list[int]]) -> None:
        """Called on no_effect: learn wall colors from blocked position."""
        if self.state != "enabled":
            return
        if action not in self.confirmed_displacements:
            return
        # Ensure we know where the player is
        if not self.player_position:
            self.find_player(curr_grid)
        if not self.player_position:
            return

        rows = len(curr_grid)
        cols = len(curr_grid[0]) if rows else 0
        bg = self._background_color(curr_grid)

        dr, dc = self.confirmed_displacements[action]
        py, px = self.player_position

        if self.player_template is None:
            return

        # Compute where the player would be if the move succeeded
        target_cells: set[tuple[int, int]] = set()
        for rel_r, rel_c, _ in self.player_template:
            nr, nc = py + rel_r + dr, px + rel_c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                target_cells.add((nr, nc))

        # Collect non-background, non-player colors in target area
        for r, c in target_cells:
            color = curr_grid[r][c]
            if color != bg and color not in self.player_colors:
                self.wall_color_evidence[color] += 1

        # Promote colors with enough evidence that we've never traversed
        newly_confirmed = set()
        for color, count in self.wall_color_evidence.items():
            if count >= 3 and color not in self.traversed_colors:
                newly_confirmed.add(color)
        if newly_confirmed - self.confirmed_walls:
            self.confirmed_walls = frozenset(self.confirmed_walls | newly_confirmed)
            logger.info("SpatialModel: confirmed wall colors: %s", self.confirmed_walls)

    def find_player(self, grid: list[list[int]]) -> Optional[tuple[int, int]]:
        """Find player position in grid. Returns (row, col) top-left or None."""
        if self.state != "enabled" or self.player_template is None:
            return None

        rows = len(grid)
        cols = len(grid[0]) if rows else 0

        # Compute bounding box of template
        max_r = max(r for r, _, _ in self.player_template)
        max_c = max(c for _, c, _ in self.player_template)

        # Search near last known position first, then full grid
        search_order = self._search_order(rows, cols, max_r, max_c)

        for sy, sx in search_order:
            if self._template_matches_at(grid, sy, sx):
                self.player_position = (sy, sx)
                self._find_failures = 0
                return (sy, sx)

        # Template not found
        self._find_failures += 1
        if self._find_failures >= 3:
            logger.info("SpatialModel: player lost 3x, state → learning")
            self.state = "learning"
            self._template_observations.clear()
            self._find_failures = 0
        return None

    def get_blocked_directions(self, grid: list[list[int]]) -> set[str]:
        """Return set of action names that would hit a wall or go OOB."""
        if self.state != "enabled" or not self.confirmed_displacements:
            return set()

        pos = self.find_player(grid)
        if pos is None:
            return set()

        py, px = pos
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        blocked: set[str] = set()

        if self.player_template is None:
            return set()

        max_r = max(r for r, _, _ in self.player_template)
        max_c = max(c for _, c, _ in self.player_template)

        for action_name, (dr, dc) in self.confirmed_displacements.items():
            ny, nx = py + dr, px + dc
            # Out of bounds check
            if ny < 0 or nx < 0 or ny + max_r >= rows or nx + max_c >= cols:
                blocked.add(action_name)
                continue
            # Wall overlap check
            if self.confirmed_walls:
                hit = False
                for rel_r, rel_c, _ in self.player_template:
                    cell = grid[ny + rel_r][nx + rel_c]
                    if cell in self.confirmed_walls:
                        hit = True
                        break
                if hit:
                    blocked.add(action_name)

        if blocked:
            logger.debug("SpatialModel: blocked from (%d,%d): %s", py, px, sorted(blocked))
        return blocked

    def on_level_up(self) -> None:
        """Soft reset on level-up: keep action mappings + wall colors, clear position.

        If disabled, re-enable learning — new level is a fresh chance.
        """
        self.player_position = None
        self._find_failures = 0
        if self.state == "disabled":
            self.state = "learning"
            self._move_count = 0
            self._template_observations.clear()
            logger.info("SpatialModel: level-up reset (was disabled → learning)")
        else:
            logger.info("SpatialModel: level-up reset (kept template + displacements + walls)")

    @property
    def player_size(self) -> Optional[tuple[int, int]]:
        """Return (height, width) of player template, or None."""
        if self.player_template is None:
            return None
        max_r = max(r for r, _, _ in self.player_template) + 1
        max_c = max(c for _, c, _ in self.player_template) + 1
        return (max_r, max_c)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _background_color(self, grid: list[list[int]]) -> int:
        """Return the most common color in the grid (background)."""
        counts: Counter = Counter()
        for row in grid:
            for cell in row:
                counts[cell] += 1
        return counts.most_common(1)[0][0] if counts else 0

    def _try_enable(self) -> None:
        """Check if template observations are consistent enough to enable."""
        # Take the most common template
        template_counts: Counter = Counter()
        for t in self._template_observations:
            template_counts[t] += 1
        best_template, count = template_counts.most_common(1)[0]
        if count < 3:
            return

        self.player_template = best_template
        self.player_colors = {color for _, _, color in best_template}

        # Lock in displacements: take median of observations
        for action, disps in self.action_displacements.items():
            if len(disps) >= 1:
                med_dr = int(median(d[0] for d in disps))
                med_dc = int(median(d[1] for d in disps))
                self.confirmed_displacements[action] = (med_dr, med_dc)

        self.state = "enabled"
        logger.info(
            "SpatialModel: state → enabled | template=%d cells, colors=%s, displacements=%s",
            len(self.player_template),
            self.player_colors,
            self.confirmed_displacements,
        )

    def _check_disable(self) -> None:
        """Disable if too many moves with no consistent player found."""
        if self.state == "learning" and self._move_count >= 10:
            consistent = len(self._template_observations)
            if consistent < 3:
                self.state = "disabled"
                logger.info(
                    "SpatialModel: state → disabled (no consistent player after %d moves)",
                    self._move_count,
                )

    def _template_matches_at(self, grid: list[list[int]], sy: int, sx: int) -> bool:
        """Check if player template matches at position (sy, sx)."""
        if self.player_template is None:
            return False
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        for rel_r, rel_c, color in self.player_template:
            r, c = sy + rel_r, sx + rel_c
            if r < 0 or r >= rows or c < 0 or c >= cols:
                return False
            if grid[r][c] != color:
                return False
        return True

    def _search_order(
        self, rows: int, cols: int, max_r: int, max_c: int
    ) -> list[tuple[int, int]]:
        """Generate search positions: near last known position first, then full grid."""
        positions: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()

        # Near last known position (spiral out)
        if self.player_position:
            py, px = self.player_position
            for radius in range(0, max(rows, cols)):
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if abs(dy) != radius and abs(dx) != radius:
                            continue  # Only check border of this radius
                        sy, sx = py + dy, px + dx
                        if 0 <= sy <= rows - max_r - 1 and 0 <= sx <= cols - max_c - 1:
                            if (sy, sx) not in seen:
                                positions.append((sy, sx))
                                seen.add((sy, sx))
                if len(positions) > 200:
                    break  # Enough near positions, fall through to full scan

        # Full grid scan for anything missed
        for sy in range(rows - max_r):
            for sx in range(cols - max_c):
                if (sy, sx) not in seen:
                    positions.append((sy, sx))
        return positions
