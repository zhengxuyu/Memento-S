"""
Grid Perception Module for ARC-AGI-3.

Analyzes 64x64 grids (values 0-15) to extract structured information that
an LLM can actually reason about, replacing the raw number dump with:

1. **Object Segmentation**: Connected-component analysis with shape classification.
2. **Background Detection**: Identifies the dominant "floor" color.
3. **Movement Tracking**: Detects what moved between frames and in which direction.
4. **Player Identification**: Heuristic tracking of the controllable object.
5. **Action-Effect Learning**: Maps GameActions to observed movement directions.
6. **Zoomed Views**: Compact hex-encoded crops around regions of interest.

The key insight: ARC-AGI-3 games present grids where VLMs and simple connected-
component methods fail because objects can be multi-colored, small, or spatially
complex.  This module provides the LLM with a *semantic description* of the grid
instead of (or in addition to) raw numbers, dramatically improving reasoning.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# Color palette for hex display and image rendering
# ============================================================================
HEX_CHARS = "0123456789ABCDEF"

# ARC-AGI color palette (RGB)
ARC_PALETTE = [
    (0, 0, 0),        # 0: black
    (0, 116, 217),     # 1: blue
    (255, 65, 54),     # 2: red
    (46, 204, 64),     # 3: green
    (255, 220, 0),     # 4: yellow
    (170, 170, 170),   # 5: gray
    (240, 18, 190),    # 6: magenta
    (255, 133, 27),    # 7: orange
    (127, 219, 255),   # 8: light blue
    (135, 12, 37),     # 9: dark red
    (128, 0, 128),     # 10: purple
    (0, 128, 0),       # 11: dark green
    (0, 128, 128),     # 12: teal
    (128, 128, 0),     # 13: olive
    (192, 192, 192),   # 14: silver
    (255, 255, 255),   # 15: white
]

# Distinct bbox colors so overlapping boxes are distinguishable
BBOX_COLORS = [
    (255, 0, 0),       # red
    (0, 255, 0),       # green
    (0, 100, 255),     # blue
    (255, 255, 0),     # yellow
    (255, 0, 255),     # magenta
    (0, 255, 255),     # cyan
    (255, 128, 0),     # orange
    (128, 255, 0),     # lime
    (255, 0, 128),     # pink
    (0, 128, 255),     # sky
    (200, 200, 200),   # light gray
    (255, 180, 180),   # salmon
]


# ============================================================================
# Data classes
# ============================================================================


@dataclass
class GridObject:
    """A detected object (connected component) in the grid."""

    obj_id: int
    color: int
    cells: list[tuple[int, int]]  # (row, col)
    bbox: tuple[int, int, int, int]  # (r_min, c_min, r_max, c_max)
    size: int
    width: int
    height: int
    center_r: float
    center_c: float
    shape: str  # "point", "hline", "vline", "rect", "border", "L", "irregular"
    fill_ratio: float  # cells / bbox_area
    is_at_edge: bool  # touches grid boundary


@dataclass
class MovedObject:
    """A detected movement between two consecutive frames."""

    colors: set[int]
    old_center: tuple[float, float]  # (row, col)
    new_center: tuple[float, float]
    dr: int  # row displacement (positive = down)
    dc: int  # col displacement (positive = right)
    size: int
    direction: str  # "UP", "DOWN", "LEFT", "RIGHT", "NONE", "DIAGONAL"


@dataclass
class GridAnalysis:
    """Full analysis result for one grid."""

    height: int
    width: int
    bg_color: int
    objects: list[GridObject]
    color_counts: dict[int, int]  # color -> total cell count

    @property
    def num_objects(self) -> int:
        return len(self.objects)


@dataclass
class FrameChange:
    """What changed between two consecutive grids."""

    total_changed: int
    change_ratio: float
    moved: list[MovedObject]
    num_appeared: int
    num_disappeared: int


# ============================================================================
# Shape classification helpers
# ============================================================================


def _classify_shape_advanced(
    cells: list[tuple[int, int]],
    r_min: int, c_min: int, r_max: int, c_max: int,
    w: int, h: int, size: int, fill: float,
) -> str:
    """Classify object shape beyond basic rect/line categories.

    Detects: cross/plus, diamond, T-shape, L-shape, U-shape, border, diagonal,
    and falls back to 'irregular'.
    """
    cell_set = set(cells)

    # Normalize cells to origin for pattern matching
    norm = {(r - r_min, c - c_min) for r, c in cells}

    # --- Cross / Plus (+) ---
    # A cross has a center row and center column that intersect.
    # Check if the object is symmetric and has a cross-like structure.
    if w >= 3 and h >= 3 and w == h:
        mid_r = h // 2
        mid_c = w // 2
        # Count cells in the center row and center column
        center_row_cells = {(r, c) for r, c in norm if r == mid_r}
        center_col_cells = {(r, c) for r, c in norm if c == mid_c}
        cross_cells = center_row_cells | center_col_cells
        if len(cross_cells) >= size * 0.8 and len(center_row_cells) >= 3 and len(center_col_cells) >= 3:
            return "cross"

    # Also detect cross in non-square bboxes
    if w >= 3 and h >= 3:
        mid_r = h // 2
        mid_c = w // 2
        center_row_cells = {(r, c) for r, c in norm if r == mid_r}
        center_col_cells = {(r, c) for r, c in norm if c == mid_c}
        cross_cells = center_row_cells | center_col_cells
        if len(cross_cells) == size and len(center_row_cells) >= 3 and len(center_col_cells) >= 3:
            return "cross"

    # --- Diamond ---
    # Diamond shape: cells form a rotated square pattern
    if w >= 3 and h >= 3 and abs(w - h) <= 1:
        mid_r = h // 2
        mid_c = w // 2
        is_diamond = True
        expected = set()
        for r in range(h):
            dist = abs(r - mid_r)
            for c in range(w):
                if abs(c - mid_c) + dist <= mid_r:
                    expected.add((r, c))
        if expected and len(norm & expected) / len(expected) > 0.8 and len(norm - expected) / max(size, 1) < 0.2:
            return "diamond"

    # --- T-shape ---
    # One full row/col at an edge + a perpendicular bar from center
    if w >= 3 and h >= 3:
        # Top T: full top row + center column
        top_row = {(0, c) for c in range(w)}
        center_col = {(r, mid_c) for r in range(h) for mid_c in [w // 2]}
        if top_row.issubset(norm) and center_col.issubset(norm) and size <= len(top_row | center_col) + 2:
            return "T-shape"
        # Bottom T
        bot_row = {(h - 1, c) for c in range(w)}
        if bot_row.issubset(norm) and center_col.issubset(norm) and size <= len(bot_row | center_col) + 2:
            return "T-shape"
        # Left T
        left_col = {(r, 0) for r in range(h)}
        center_row = {(mid_r, c) for c in range(w) for mid_r in [h // 2]}
        if left_col.issubset(norm) and center_row.issubset(norm) and size <= len(left_col | center_row) + 2:
            return "T-shape"
        # Right T
        right_col = {(r, w - 1) for r in range(h)}
        if right_col.issubset(norm) and center_row.issubset(norm) and size <= len(right_col | center_row) + 2:
            return "T-shape"

    # --- L-shape ---
    # Two perpendicular bars meeting at a corner
    if w >= 2 and h >= 2 and 0.2 < fill < 0.6:
        corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
        for cr, cc in corners:
            row_bar = {(cr, c) for c in range(w)}
            col_bar = {(r, cc) for r in range(h)}
            l_cells = row_bar | col_bar
            if l_cells.issubset(norm) and len(l_cells) >= size * 0.8:
                return "L-shape"

    # --- U-shape ---
    if w >= 3 and h >= 3 and 0.4 < fill < 0.75:
        # Bottom U: left col + right col + bottom row
        left_col = {(r, 0) for r in range(h)}
        right_col = {(r, w - 1) for r in range(h)}
        bot_row = {(h - 1, c) for c in range(w)}
        u_cells = left_col | right_col | bot_row
        if len(norm & u_cells) / len(u_cells) > 0.8:
            return "U-shape"

    # --- Border / hollow rectangle ---
    if 0.3 < fill <= 0.85:
        border_cells = sum(
            1
            for r, c in norm
            if r in (0, h - 1) or c in (0, w - 1)
        )
        if border_cells / size > 0.75:
            return "border"

    # --- Diagonal line ---
    if size >= 3 and (w == h or abs(w - h) <= 1):
        diag1 = {(i, i) for i in range(min(w, h))}
        diag2 = {(i, w - 1 - i) for i in range(min(w, h))}
        if len(norm & diag1) / max(len(diag1), 1) > 0.8 or len(norm & diag2) / max(len(diag2), 1) > 0.8:
            return "diagonal"

    return "irregular"


def _cluster_nearby_objects(
    objects: list[GridObject],
    max_gap: int = 2,
    max_obj_size: int = 10,
) -> list[dict]:
    """Cluster nearby small objects into composite shapes.

    Merges small objects (size <= max_obj_size) that are within `max_gap`
    cells of each other into a single composite, then classifies the
    merged shape.

    Returns a list of dicts:
        {"cells": [...], "colors": set, "obj_ids": [...], "shape": str,
         "center": (r, c), "bbox": (r_min, c_min, r_max, c_max)}
    """
    from collections import deque

    small = [o for o in objects if o.size <= max_obj_size]
    if len(small) < 2:
        return []

    # Build adjacency: two objects are neighbours if any of their cells
    # are within max_gap of each other (Chebyshev distance).
    n = len(small)
    adj: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        cells_i = set(small[i].cells)
        for j in range(i + 1, n):
            # Quick bbox check first
            oi, oj = small[i], small[j]
            if (abs(oi.center_r - oj.center_r) > oi.height + oj.height + max_gap or
                    abs(oi.center_c - oj.center_c) > oi.width + oj.width + max_gap):
                continue
            # Detailed cell check
            close = False
            for r2, c2 in small[j].cells:
                for r1, c1 in small[i].cells:
                    if abs(r1 - r2) <= max_gap and abs(c1 - c2) <= max_gap:
                        close = True
                        break
                if close:
                    break
            if close:
                adj[i].append(j)
                adj[j].append(i)

    # BFS to find connected components
    visited = [False] * n
    composites: list[dict] = []
    for start in range(n):
        if visited[start]:
            continue
        queue = deque([start])
        visited[start] = True
        component: list[int] = []
        while queue:
            idx = queue.popleft()
            component.append(idx)
            for nb in adj[idx]:
                if not visited[nb]:
                    visited[nb] = True
                    queue.append(nb)

        if len(component) < 2:
            continue  # Single object, not a cluster

        # Merge cells
        all_cells: list[tuple[int, int]] = []
        colors: set[int] = set()
        obj_ids: list[int] = []
        for idx in component:
            all_cells.extend(small[idx].cells)
            colors.add(small[idx].color)
            obj_ids.append(small[idx].obj_id)

        rs = [r for r, c in all_cells]
        cs = [c for r, c in all_cells]
        r_min, r_max = min(rs), max(rs)
        c_min, c_max = min(cs), max(cs)
        w = c_max - c_min + 1
        h = r_max - r_min + 1
        size = len(all_cells)
        fill = size / (w * h) if w * h > 0 else 0

        # Classify merged shape
        if size == 1:
            shape = "point"
        elif h == 1:
            shape = "hline"
        elif w == 1:
            shape = "vline"
        elif fill > 0.85:
            shape = "rect"
        else:
            shape = _classify_shape_advanced(
                all_cells, r_min, c_min, r_max, c_max, w, h, size, fill,
            )

        center_r = sum(rs) / len(rs)
        center_c = sum(cs) / len(cs)

        composites.append({
            "cells": all_cells,
            "colors": colors,
            "obj_ids": obj_ids,
            "shape": shape,
            "center": (center_r, center_c),
            "bbox": (r_min, c_min, r_max, c_max),
            "size": size,
        })

    return composites


# ============================================================================
# Main perception class
# ============================================================================


class GridPerception:
    """Perception engine for ARC-AGI-3 grids.

    Maintains state across frames to track the player and learn action effects.
    Create one instance per game (agent lifetime).
    """

    def __init__(self) -> None:
        # Player tracking
        self._player_obj: Optional[GridObject] = None
        self._player_color_votes: Counter = Counter()

        # Action-effect learning: action_name -> list of (dr, dc)
        self._action_effects: dict[str, list[tuple[int, int]]] = {}

    # ------------------------------------------------------------------ #
    #  Core analysis
    # ------------------------------------------------------------------ #

    def analyze_grid(self, grid: list[list[int]]) -> GridAnalysis:
        """Segment a single grid into objects with properties."""
        H = len(grid)
        W = len(grid[0]) if H > 0 else 0

        # Color histogram
        color_counts: dict[int, int] = {}
        for row in grid:
            for v in row:
                color_counts[v] = color_counts.get(v, 0) + 1

        # Background = most common color
        bg = max(color_counts, key=color_counts.get) if color_counts else 0

        # Connected components via BFS (4-connected, per color)
        visited = [[False] * W for _ in range(H)]
        objects: list[GridObject] = []
        obj_id = 0

        for r in range(H):
            for c in range(W):
                if grid[r][c] != bg and not visited[r][c]:
                    color = grid[r][c]
                    cells = self._bfs(grid, visited, r, c, color, H, W)
                    obj = self._build_object(obj_id, color, cells, H, W)
                    objects.append(obj)
                    obj_id += 1

        # Sort by size descending for easier reading
        objects.sort(key=lambda o: o.size, reverse=True)
        for i, obj in enumerate(objects):
            obj.obj_id = i

        return GridAnalysis(
            height=H, width=W, bg_color=bg,
            objects=objects, color_counts=color_counts,
        )

    def compute_diff(
        self, prev_grid: list[list[int]], curr_grid: list[list[int]]
    ) -> FrameChange:
        """Detect changes between two grids, including movement.

        Uses **per-color** tracking: for each non-background color, find
        cells where that color disappeared and where it appeared.  This
        catches objects moving over *any* surface, not just over the
        background color.
        """
        H = len(prev_grid)
        W = len(prev_grid[0]) if H > 0 else 0

        prev_bg = self._quick_bg(prev_grid, H, W)
        curr_bg = self._quick_bg(curr_grid, H, W)
        bg_colors = {prev_bg, curr_bg}

        # Per-color: cells where a color vanished / appeared
        # color -> list of (r, c)
        color_lost: dict[int, list[tuple[int, int]]] = {}
        color_gained: dict[int, list[tuple[int, int]]] = {}

        changed_total = 0
        num_appeared = 0   # bg -> non-bg (any surface)
        num_disappeared = 0  # non-bg -> bg

        for r in range(H):
            for c in range(W):
                pv, cv = prev_grid[r][c], curr_grid[r][c]
                if pv == cv:
                    continue
                changed_total += 1

                # Track per-color disappearance / appearance
                if pv not in bg_colors:
                    color_lost.setdefault(pv, []).append((r, c))
                if cv not in bg_colors:
                    color_gained.setdefault(cv, []).append((r, c))

                # Legacy counters
                if pv not in bg_colors and cv in bg_colors:
                    num_disappeared += 1
                elif pv in bg_colors and cv not in bg_colors:
                    num_appeared += 1

        total_cells = H * W
        ratio = changed_total / total_cells if total_cells > 0 else 0.0

        # Detect movements per color, then merge
        moved = self._detect_movements_by_color(color_lost, color_gained)

        return FrameChange(
            total_changed=changed_total,
            change_ratio=ratio,
            moved=moved,
            num_appeared=num_appeared,
            num_disappeared=num_disappeared,
        )

    # ------------------------------------------------------------------ #
    #  High-level description for LLM
    # ------------------------------------------------------------------ #

    def describe_frame(
        self,
        frame: list[list[list[int]]],
        prev_frame: Optional[list[list[list[int]]]] = None,
        last_action: Optional[str] = None,
    ) -> str:
        """Produce a structured LLM-readable description of the frame.

        This REPLACES the raw grid dump with a much more informative
        semantic analysis.

        Args:
            frame: List of grids (from FrameData.frame).
            prev_frame: Previous frame's grids (for diff).
            last_action: The action name that produced this frame.

        Returns:
            Multi-line structured text description.
        """
        parts: list[str] = []

        for g_idx, grid in enumerate(frame):
            analysis = self.analyze_grid(grid)
            parts.append(self._format_analysis(analysis, g_idx))

            # Frame diff
            if prev_frame and g_idx < len(prev_frame):
                change = self.compute_diff(prev_frame[g_idx], grid)
                if change.total_changed > 0:
                    diff_text = self._format_diff(change, last_action)
                    parts.append(diff_text)

                    # Learn action effects
                    if last_action and change.moved:
                        self._learn_action_effect(last_action, change.moved)

                    # Update player tracking
                    if change.moved:
                        self._update_player_tracking(change.moved, analysis)

                    # Zoomed view around changed area
                    zoom = self._zoomed_view(grid, change)
                    if zoom:
                        parts.append(zoom)
                else:
                    parts.append(
                        f"[Grid {g_idx} unchanged — last action had NO EFFECT]"
                    )

        # Action-effect summary
        effects = self._format_action_effects()
        if effects:
            parts.append(effects)

        # Player info
        player_info = self._format_player_info()
        if player_info:
            parts.append(player_info)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    #  BFS and object building
    # ------------------------------------------------------------------ #

    @staticmethod
    def _bfs(
        grid: list[list[int]],
        visited: list[list[bool]],
        start_r: int,
        start_c: int,
        color: int,
        H: int,
        W: int,
    ) -> list[tuple[int, int]]:
        """4-connected flood fill for a single color."""
        cells: list[tuple[int, int]] = []
        queue = deque([(start_r, start_c)])
        visited[start_r][start_c] = True

        while queue:
            r, c = queue.popleft()
            cells.append((r, c))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and not visited[nr][nc]:
                    if grid[nr][nc] == color:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

        return cells

    @staticmethod
    def _build_object(
        obj_id: int,
        color: int,
        cells: list[tuple[int, int]],
        grid_h: int,
        grid_w: int,
    ) -> GridObject:
        """Build a GridObject from a set of cells."""
        rs = [p[0] for p in cells]
        cs = [p[1] for p in cells]
        r_min, r_max = min(rs), max(rs)
        c_min, c_max = min(cs), max(cs)
        w = c_max - c_min + 1
        h = r_max - r_min + 1
        bbox_area = w * h
        fill = len(cells) / bbox_area if bbox_area > 0 else 0.0
        size = len(cells)

        # Shape classification
        if size == 1:
            shape = "point"
        elif h == 1 and w > 1:
            shape = "hline"
        elif w == 1 and h > 1:
            shape = "vline"
        elif fill > 0.85:
            shape = "rect"
        else:
            shape = _classify_shape_advanced(cells, r_min, c_min, r_max, c_max, w, h, size, fill)

        is_at_edge = r_min == 0 or c_min == 0 or r_max >= grid_h - 1 or c_max >= grid_w - 1

        return GridObject(
            obj_id=obj_id,
            color=color,
            cells=cells,
            bbox=(r_min, c_min, r_max, c_max),
            size=size,
            width=w,
            height=h,
            center_r=sum(rs) / len(rs),
            center_c=sum(cs) / len(cs),
            shape=shape,
            fill_ratio=fill,
            is_at_edge=is_at_edge,
        )

    # ------------------------------------------------------------------ #
    #  Movement detection
    # ------------------------------------------------------------------ #

    def _detect_movements_by_color(
        self,
        color_lost: dict[int, list[tuple[int, int]]],
        color_gained: dict[int, list[tuple[int, int]]],
    ) -> list[MovedObject]:
        """Match per-color lost/gained cell clusters as object movements.

        For each color that has both lost and gained cells, cluster each
        set and match lost<->gained clusters by proximity and size to
        identify movement.
        """
        moved: list[MovedObject] = []

        # Process each color that appears in both lost and gained
        all_colors = set(color_lost.keys()) & set(color_gained.keys())
        for color in all_colors:
            lost_cells = color_lost[color]
            gained_cells = color_gained[color]

            lost_clusters = self._cluster_cells(lost_cells)
            gained_clusters = self._cluster_cells(gained_cells)

            used_gained: set[int] = set()

            for lc in lost_clusters:
                lc_center = self._centroid(lc)
                lc_size = len(lc)

                best_dist = float("inf")
                best_idx = -1

                for i, gc in enumerate(gained_clusters):
                    if i in used_gained:
                        continue
                    gc_size = len(gc)
                    if gc_size == 0:
                        continue
                    size_ratio = min(lc_size, gc_size) / max(lc_size, gc_size)
                    if size_ratio < 0.4:
                        continue
                    gc_center = self._centroid(gc)
                    dist = abs(gc_center[0] - lc_center[0]) + abs(
                        gc_center[1] - lc_center[1]
                    )
                    if dist < best_dist and dist < 20:
                        best_dist = dist
                        best_idx = i

                if best_idx >= 0:
                    used_gained.add(best_idx)
                    gc = gained_clusters[best_idx]
                    gc_center = self._centroid(gc)

                    dr = round(gc_center[0] - lc_center[0])
                    dc = round(gc_center[1] - lc_center[1])

                    if dr == 0 and dc == 0:
                        continue  # reshape, not movement

                    direction = self._direction_name(dr, dc)

                    moved.append(
                        MovedObject(
                            colors={color},
                            old_center=lc_center,
                            new_center=gc_center,
                            dr=dr,
                            dc=dc,
                            size=len(gc),
                            direction=direction,
                        )
                    )

        return moved

    @staticmethod
    def _cluster_cells(
        cells: list[tuple[int, int]],
    ) -> list[list[tuple[int, int]]]:
        """Cluster cells into groups of 8-connected neighbours."""
        if not cells:
            return []

        cell_set = set(cells)
        visited: set[tuple[int, int]] = set()
        clusters: list[list[tuple[int, int]]] = []

        for cell in cells:
            if cell in visited:
                continue
            cluster: list[tuple[int, int]] = []
            queue = deque([cell])
            visited.add(cell)
            while queue:
                r, c = queue.popleft()
                cluster.append((r, c))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nb = (r + dr, c + dc)
                        if nb in cell_set and nb not in visited:
                            visited.add(nb)
                            queue.append(nb)
            clusters.append(cluster)

        return clusters

    @staticmethod
    def _centroid(cells: list[tuple[int, int]]) -> tuple[float, float]:
        if not cells:
            return (0.0, 0.0)
        r = sum(c[0] for c in cells) / len(cells)
        c_ = sum(c[1] for c in cells) / len(cells)
        return (r, c_)

    @staticmethod
    def _direction_name(dr: int, dc: int) -> str:
        if dr == 0 and dc == 0:
            return "NONE"
        if abs(dr) > 0 and abs(dc) > 0:
            parts = []
            parts.append("UP" if dr < 0 else "DOWN")
            parts.append("LEFT" if dc < 0 else "RIGHT")
            return "-".join(parts)
        if dr < 0:
            return "UP"
        if dr > 0:
            return "DOWN"
        if dc < 0:
            return "LEFT"
        return "RIGHT"

    # ------------------------------------------------------------------ #
    #  Player tracking
    # ------------------------------------------------------------------ #

    def _update_player_tracking(
        self, movements: list[MovedObject], analysis: GridAnalysis
    ) -> None:
        """Update player identification based on observed movement."""
        if not movements:
            return

        # The player is the object that moves in response to actions.
        # Heuristic: the smallest moving cluster is most likely the player.
        smallest = min(movements, key=lambda m: m.size)

        # Find matching objects in the current analysis
        player_obj = None
        for obj in analysis.objects:
            dist = (
                abs(obj.center_r - smallest.new_center[0])
                + abs(obj.center_c - smallest.new_center[1])
            )
            if dist < 3:
                player_obj = obj
                self._player_obj = obj
                self._player_color_votes[obj.color] += 1
                break

        # Also vote for nearby objects that are likely part of the same
        # multi-color player entity (e.g. body=color9, head=color12).
        # Only consider objects whose color also moved this step, to avoid
        # voting for static game elements (patterns, decorations) near the
        # player.
        if player_obj is not None:
            moving_colors: set[int] = set()
            for m in movements:
                moving_colors.update(m.colors)
            for obj in analysis.objects:
                if obj is player_obj:
                    continue
                if obj.size >= 50:
                    continue
                if obj.color not in moving_colors:
                    continue
                ndist = (
                    abs(obj.center_r - player_obj.center_r)
                    + abs(obj.center_c - player_obj.center_c)
                )
                if ndist <= 5:  # within one step
                    self._player_color_votes[obj.color] += 1

    def _learn_action_effect(
        self, action: str, movements: list[MovedObject]
    ) -> None:
        """Record the observed displacement caused by an action."""
        if not movements:
            return
        # Use the smallest/player-like movement
        primary = min(movements, key=lambda m: m.size)
        dr, dc = primary.dr, primary.dc
        # Guard against teleportation: only learn clean ±STEP_SIZE moves
        # (exactly 5 cells in one axis, 0 in the other)
        if not ((abs(dr) == 5 and dc == 0) or (dr == 0 and abs(dc) == 5)):
            return
        if action not in self._action_effects:
            self._action_effects[action] = []
        self._action_effects[action].append((dr, dc))

    # ------------------------------------------------------------------ #
    #  Formatting helpers
    # ------------------------------------------------------------------ #

    def _format_analysis(self, analysis: GridAnalysis, grid_idx: int) -> str:
        """Format a GridAnalysis into LLM-readable text."""
        lines: list[str] = []
        lines.append(
            f"## Grid {grid_idx} ({analysis.height}x{analysis.width}, "
            f"bg=color {analysis.bg_color})"
        )

        # Color summary
        non_bg = {
            c: n
            for c, n in analysis.color_counts.items()
            if c != analysis.bg_color and n > 0
        }
        if non_bg:
            color_str = ", ".join(
                f"c{c}:{n}" for c, n in sorted(non_bg.items(), key=lambda x: -x[1])
            )
            lines.append(f"Non-bg colors: {color_str}")

        lines.append(f"Objects detected: {analysis.num_objects}")

        if not analysis.objects:
            return "\n".join(lines)

        # Group objects by role heuristic
        large: list[GridObject] = []  # > 100 cells — likely walls/borders
        medium: list[GridObject] = []  # 10-100
        small: list[GridObject] = []  # < 10

        for obj in analysis.objects:
            if obj.size > 100:
                large.append(obj)
            elif obj.size >= 10:
                medium.append(obj)
            else:
                small.append(obj)

        if large:
            lines.append(f"\nWalls/borders: {len(large)} large objects (colors: " +
                        ", ".join(str(o.color) for o in large[:5]) + ")")

        if medium:
            lines.append("\nMedium objects:")
            for obj in medium[:5]:
                player_tag = " [PLAYER]" if obj is self._player_obj else ""
                shape_tag = ""
                if obj.shape in ("cross", "diamond", "T-shape", "L-shape"):
                    shape_tag = f" **{obj.shape.upper()}**"
                lines.append(
                    f"  #{obj.obj_id} c{obj.color} {obj.size}cells {obj.shape} "
                    f"center=({obj.center_r:.0f},{obj.center_c:.0f})"
                    f"{player_tag}{shape_tag}"
                )

        if small:
            lines.append(f"\nSmall: {len(small)} objects")
            for obj in small[:5]:
                player_tag = " [PLAYER]" if obj is self._player_obj else ""
                shape_tag = ""
                if obj.shape in ("cross", "diamond", "T-shape", "L-shape"):
                    shape_tag = f" **{obj.shape.upper()}**"
                lines.append(
                    f"  #{obj.obj_id} c{obj.color} {obj.size}cells "
                    f"at ({obj.center_r:.0f},{obj.center_c:.0f})"
                    f"{player_tag}{shape_tag}"
                )
            if len(small) > 5:
                lines.append(f"  +{len(small) - 5} more")

        # Composite shape detection: cluster nearby small objects
        composites = _cluster_nearby_objects(analysis.objects)
        if composites:
            lines.append("\n*** COMPOSITE SHAPES (nearby small objects merged): ***")
            for comp in composites:
                shape = comp["shape"]
                colors_str = ",".join(str(c) for c in sorted(comp["colors"]))
                obj_ids_str = ",".join(f"#{i}" for i in comp["obj_ids"])
                cr, cc = int(comp['center'][0]), int(comp['center'][1])
                highlight = ""
                if shape in ("cross", "diamond", "T-shape", "L-shape"):
                    highlight = (
                        f"\n  ==> {shape.upper()} DETECTED! Interactive target!"
                        f"\n  ==> ACTION: Call navigate_to({cr}, {cc}) to reach it, then step ON it."
                        f"\n  ==> Do NOT manually chain ACTION1/ACTION3 — use navigate_to!"
                    )
                lines.append(
                    f"  Objects {obj_ids_str} (colors {colors_str}): "
                    f"{comp['size']} cells merged -> {shape} shape "
                    f"at center ({cr},{cc}) "
                    f"bbox ({comp['bbox'][0]},{comp['bbox'][1]})-({comp['bbox'][2]},{comp['bbox'][3]})"
                    f"{highlight}"
                )

        # UI region detection: bottom 3 rows often have score/status
        bottom_objs = [
            obj
            for obj in analysis.objects
            if obj.bbox[2] >= analysis.height - 3
        ]
        if bottom_objs:
            lines.append(
                f"\nBottom-edge objects (possible UI): "
                f"{len(bottom_objs)} objects in last 3 rows"
            )

        return "\n".join(lines)

    def _format_diff(self, change: FrameChange, last_action: Optional[str]) -> str:
        """Format a FrameChange into LLM-readable text."""
        lines: list[str] = []
        pct = change.change_ratio * 100

        act_str = f" (after {last_action})" if last_action else ""
        lines.append(f"### Frame Changes{act_str}:")
        lines.append(
            f"  {change.total_changed} cells changed ({pct:.1f}% of grid)"
        )

        if change.moved:
            for m in change.moved:
                lines.append(
                    f"  MOVEMENT: {m.size}-cell object "
                    f"({m.old_center[0]:.0f},{m.old_center[1]:.0f}) -> "
                    f"({m.new_center[0]:.0f},{m.new_center[1]:.0f}) "
                    f"= {m.direction} (dr={m.dr}, dc={m.dc})"
                )

        if change.num_appeared > 0 and not change.moved:
            lines.append(f"  {change.num_appeared} cells appeared (new object?)")
        if change.num_disappeared > 0 and not change.moved:
            lines.append(
                f"  {change.num_disappeared} cells disappeared (object removed?)"
            )

        return "\n".join(lines)

    def _format_action_effects(self) -> str:
        """Summarize learned action-effect mappings."""
        if not self._action_effects:
            return ""

        lines: list[str] = ["### Learned Action Effects:"]
        for action, effects in sorted(self._action_effects.items()):
            if not effects:
                continue
            # Most common direction
            dir_counts: dict[str, int] = {}
            for dr, dc in effects:
                d = self._direction_name(dr, dc)
                dir_counts[d] = dir_counts.get(d, 0) + 1

            top_dir = max(dir_counts, key=dir_counts.get)
            count = dir_counts[top_dir]
            total = len(effects)
            noop = sum(1 for dr, dc in effects if dr == 0 and dc == 0)

            if noop == total:
                lines.append(f"  {action} -> NO MOVEMENT ({total} observations)")
            else:
                lines.append(
                    f"  {action} -> {top_dir} "
                    f"({count}/{total} times"
                    f"{f', {noop} no-ops' if noop else ''})"
                )

        return "\n".join(lines)

    def _format_player_info(self) -> str:
        """Summary of current player identification."""
        if self._player_obj is None:
            return ""

        obj = self._player_obj
        most_common = self._player_color_votes.most_common(1)
        color_info = (
            f"color {most_common[0][0]} (seen {most_common[0][1]}x)"
            if most_common
            else f"color {obj.color}"
        )

        qr = (int(obj.center_r) // 5) * 5
        qc = (int(obj.center_c) // 5) * 5
        return (
            f"### Player Tracking:\n"
            f"  Identified: #{obj.obj_id}, {color_info}, "
            f"{obj.size} cells, {obj.shape} "
            f"({obj.height}x{obj.width}), "
            f"center=({obj.center_r:.0f},{obj.center_c:.0f}), "
            f"grid-pos=({qr},{qc})"
        )

    # ------------------------------------------------------------------ #
    #  Zoomed view
    # ------------------------------------------------------------------ #

    def _zoomed_view(
        self,
        grid: list[list[int]],
        change: FrameChange,
        max_size: int = 12,
    ) -> str:
        """Produce a compact hex-encoded crop around the area of interest.

        Focuses on the player or the changed region.
        """
        H = len(grid)
        W = len(grid[0]) if H > 0 else 0

        # Determine center of interest
        if self._player_obj is not None:
            cr = int(self._player_obj.center_r)
            cc = int(self._player_obj.center_c)
            label = "player area"
        elif change.moved:
            m = change.moved[0]
            cr = int(m.new_center[0])
            cc = int(m.new_center[1])
            label = "movement area"
        else:
            return ""

        # Compute crop bounds
        half = max_size // 2
        r_min = max(0, cr - half)
        r_max = min(H, cr + half)
        c_min = max(0, cc - half)
        c_max = min(W, cc + half)

        lines: list[str] = [
            f"### Zoomed View ({label}, "
            f"rows {r_min}-{r_max - 1}, cols {c_min}-{c_max - 1}):"
        ]

        # Column header
        col_header = "    " + "".join(
            str(c % 10) for c in range(c_min, c_max)
        )
        lines.append(col_header)

        for r in range(r_min, r_max):
            row_str = "".join(
                HEX_CHARS[grid[r][c]] for c in range(c_min, c_max)
            )
            lines.append(f" {r:2d} {row_str}")

        lines.append(
            "(hex: 0-9=colors 0-9, A=10, B=11, C=12, D=13, E=14, F=15)"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def _quick_bg(grid: list[list[int]], H: int, W: int) -> int:
        """Fast background detection via sampling."""
        counts: dict[int, int] = {}
        # Sample corners + edges + center for speed
        samples = []
        for r in (0, H // 4, H // 2, 3 * H // 4, H - 1):
            for c in (0, W // 4, W // 2, 3 * W // 4, W - 1):
                if 0 <= r < H and 0 <= c < W:
                    samples.append(grid[r][c])
        # Also sample full first/last rows
        if H > 0:
            samples.extend(grid[0])
            samples.extend(grid[H - 1])

        for v in samples:
            counts[v] = counts.get(v, 0) + 1
        return max(counts, key=counts.get) if counts else 0

    def reset(self) -> None:
        """Reset perception state for a new game/episode."""
        self._player_obj = None
        self._player_color_votes.clear()
        self._action_effects.clear()

    # ------------------------------------------------------------------ #
    #  Image rendering with bounding boxes
    # ------------------------------------------------------------------ #

    def render_grid(
        self,
        grid: list[list[int]],
        analysis: Optional[GridAnalysis] = None,
        scale: int = 8,
        show_labels: bool = True,
        max_boxes: int = 30,
    ):
        """Render a grid as a PIL Image with detected object bounding boxes.

        Args:
            grid: 2-D list of color values (0-15).
            analysis: Pre-computed GridAnalysis (computed on the fly if None).
            scale: Pixel size per grid cell.
            show_labels: Draw object id / color labels next to boxes.
            max_boxes: Maximum bounding boxes to draw (largest first).

        Returns:
            ``PIL.Image.Image`` or *None* if Pillow is not installed.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None

        if analysis is None:
            analysis = self.analyze_grid(grid)

        H, W = analysis.height, analysis.width
        img = Image.new("RGB", (W * scale, H * scale))
        pixels = img.load()

        # Paint grid cells
        for r in range(H):
            for c in range(W):
                color = ARC_PALETTE[min(grid[r][c], 15)]
                for dy in range(scale):
                    for dx in range(scale):
                        pixels[c * scale + dx, r * scale + dy] = color

        draw = ImageDraw.Draw(img)

        # Try to get a small font for labels
        font = None
        if show_labels:
            for font_path in (
                "/System/Library/Fonts/Menlo.ttc",
                "/System/Library/Fonts/SFNSMono.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            ):
                try:
                    font = ImageFont.truetype(font_path, max(scale, 10))
                    break
                except (OSError, IOError):
                    continue
            if font is None:
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None

        # Draw bounding boxes
        objects_to_draw = analysis.objects[:max_boxes]
        for idx, obj in enumerate(objects_to_draw):
            bbox_color = BBOX_COLORS[idx % len(BBOX_COLORS)]

            r_min, c_min, r_max, c_max = obj.bbox
            x0 = c_min * scale
            y0 = r_min * scale
            x1 = (c_max + 1) * scale - 1
            y1 = (r_max + 1) * scale - 1

            # Draw 2-pixel wide rectangle
            draw.rectangle([x0, y0, x1, y1], outline=bbox_color, width=2)

            # Player gets a thicker box
            if obj is self._player_obj:
                draw.rectangle(
                    [x0 - 1, y0 - 1, x1 + 1, y1 + 1],
                    outline=(255, 255, 255),
                    width=1,
                )

            # Label
            if show_labels and font is not None:
                label = f"#{obj.obj_id} c{obj.color}"
                if obj is self._player_obj:
                    label += " P"
                # Position label above the box, or below if near top edge
                lx = x0
                ly = y0 - scale - 2
                if ly < 0:
                    ly = y1 + 2
                draw.text((lx, ly), label, fill=bbox_color, font=font)

        # -- Direction indicator: UP arrow + "UP" label in top-right corner --
        img_w, img_h = img.size
        arrow_color = (255, 255, 255)
        outline_color = (0, 0, 0)
        margin = 4
        # Arrow dimensions
        arrow_h = min(5 * scale, img_h // 6)
        arrow_w = arrow_h // 2
        cx = img_w - margin - arrow_w  # center x of arrow
        top_y = margin
        bot_y = top_y + arrow_h
        # Draw outline first (black), then white on top for visibility
        for color_pass, width_pass in ((outline_color, 4), (arrow_color, 2)):
            # Shaft
            draw.line(
                [(cx, top_y + arrow_w), (cx, bot_y)],
                fill=color_pass, width=width_pass,
            )
            # Arrowhead (triangle)
            draw.polygon(
                [
                    (cx, top_y),                        # tip
                    (cx - arrow_w // 2, top_y + arrow_w),  # bottom-left
                    (cx + arrow_w // 2, top_y + arrow_w),  # bottom-right
                ],
                fill=color_pass,
            )
        # "UP" text label
        if font is not None:
            label_x = cx - arrow_w
            label_y = bot_y + 2
            draw.text((label_x + 1, label_y + 1), "UP", fill=outline_color, font=font)
            draw.text((label_x, label_y), "UP", fill=arrow_color, font=font)

        return img

    def render_frame(
        self,
        frame: list[list[list[int]]],
        scale: int = 8,
        show_labels: bool = True,
        max_boxes: int = 30,
    ):
        """Render all grids in a frame side-by-side with bounding boxes.

        Returns:
            ``PIL.Image.Image`` or *None* if Pillow is not installed.
        """
        try:
            from PIL import Image
        except ImportError:
            return None

        images = []
        for grid in frame:
            analysis = self.analyze_grid(grid)
            img = self.render_grid(
                grid, analysis=analysis, scale=scale,
                show_labels=show_labels, max_boxes=max_boxes,
            )
            if img is not None:
                images.append(img)

        if not images:
            return None
        if len(images) == 1:
            return images[0]

        # Side-by-side with 4px gap
        gap = 4
        total_w = sum(im.width for im in images) + gap * (len(images) - 1)
        max_h = max(im.height for im in images)
        combined = Image.new("RGB", (total_w, max_h), (40, 40, 40))
        x_offset = 0
        for im in images:
            combined.paste(im, (x_offset, 0))
            x_offset += im.width + gap

        return combined
