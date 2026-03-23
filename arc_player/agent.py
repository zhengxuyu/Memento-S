"""ARC Game Player Agent with structured file-based memory.

Lean agent: 1 LLM call per game action, memory tools processed inline.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI as OpenAIClient
import openai

from arcengine import GameAction, GameState

from .memory_manager import MemoryManager
from .exploration_tree import ExplorationTree

logger = logging.getLogger(__name__)

GAME_ACTIONS = {f"ACTION{i}" for i in range(1, 7)}
API_RETRIES = 3
MESSAGE_WINDOW = 30
MAX_TOOL_ROUNDS = 4  # Max LLM calls per step before forcing action
MAX_CONSECUTIVE_FAILURES = 3  # After this many step-level failures, force a random action
STUCK_THRESHOLD = 20  # Steps without score change before hypothesis nudge
HYPOTHESIS_INTERVAL = 10  # Re-nudge every N steps while stuck


COLOR_CHARS = "0123456789ABCDEF"  # map color index → single char
FIB_OFFSETS = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55]  # Fibonacci-spaced lookback
MAX_MAP_SNAPSHOTS = 100  # Keep last N snapshots in memory


def _grid_to_minimap(grid: list[list[int]]) -> list[list[str]]:
    """Downsample 64x64 grid to 12x12 character map (5x5 blocks, skip border)."""
    if not grid or not grid[0]:
        return []
    rows, cols = len(grid), len(grid[0])
    result = []
    for br in range(4, rows - 4, 5):
        row_chars = []
        for bc in range(4, cols - 4, 5):
            block_colors: Counter[int] = Counter()
            for dr in range(min(5, rows - br)):
                for dc in range(min(5, cols - bc)):
                    block_colors[grid[br + dr][bc + dc]] += 1
            dominant = block_colors.most_common(1)[0][0]
            ch = COLOR_CHARS[dominant] if dominant < len(COLOR_CHARS) else "?"
            row_chars.append(ch)
        result.append(row_chars)
    return result


def _render_minimap(minimap: list[list[str]], step: int) -> str:
    """Render a single minimap with row/col headers."""
    lines = []
    # Column header
    col_headers = "    "
    for i, bc in enumerate(range(4, 60, 5)):
        col_headers += f"{bc:>3} "
    lines.append(col_headers)
    for i, br in enumerate(range(4, 60, 5)):
        if i < len(minimap):
            line = f"{br:>3} " + "".join(f"  {ch} " for ch in minimap[i])
            lines.append(line)
    return "\n".join(lines)


def _render_map_history(snapshots: list[tuple[int, list[list[str]]]]) -> str:
    """Render multiple map snapshots at Fibonacci intervals into a single document.

    snapshots: list of (step, minimap) ordered by step ascending.
    Picks 10 snapshots at Fibonacci-spaced offsets from the latest.
    """
    if not snapshots:
        return "(no snapshots)"

    # Select Fibonacci-spaced snapshots from the end
    n = len(snapshots)
    selected: list[tuple[int, list[list[str]]]] = []
    seen_indices: set[int] = set()
    for offset in FIB_OFFSETS:
        idx = n - 1 - offset
        if idx < 0:
            break
        if idx not in seen_indices:
            seen_indices.add(idx)
            selected.append(snapshots[idx])

    # Sort by step ascending
    selected.sort(key=lambda x: x[0])

    # Collect all colors seen across all snapshots
    colors_seen: set[str] = set()
    for _, mm in selected:
        for row in mm:
            colors_seen.update(row)

    # Render each snapshot
    parts = []
    for step, mm in selected:
        header = f"### Step {step}"
        parts.append(header + "\n" + _render_minimap(mm, step))

    # Legend
    legend_parts = []
    for ch in sorted(colors_seen):
        idx = COLOR_CHARS.index(ch) if ch in COLOR_CHARS else -1
        if idx >= 0:
            legend_parts.append(f"{ch}=c{idx}")
    parts.append(f"\nLegend: {', '.join(legend_parts)}")
    parts.append(f"Each cell = 5x5 block | Fibonacci spacing: recent=dense, old=sparse")

    return "\n\n".join(parts)


def _compact_grid(grid: list[list[int]]) -> str:
    """Compress a 2D grid into sparse representation."""
    if not grid or not grid[0]:
        return "(empty)"
    rows, cols = len(grid), len(grid[0])
    counter: Counter[int] = Counter()
    for row in grid:
        counter.update(row)
    bg = counter.most_common(1)[0][0]

    color_cells: dict[int, list[tuple[int, int]]] = {}
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val != bg:
                color_cells.setdefault(val, []).append((r, c))

    lines = [f"{rows}x{cols}, bg=color {bg}"]
    if not color_cells:
        return lines[0] + " (all background)"
    for color in sorted(color_cells):
        cells = color_cells[color]
        if len(cells) > 50:
            rs = [r for r, c in cells]
            cs = [c for r, c in cells]
            lines.append(f"c{color}: {len(cells)} cells, rows {min(rs)}-{max(rs)}, cols {min(cs)}-{max(cs)}")
        else:
            coords = ", ".join(f"({r},{c})" for r, c in cells)
            lines.append(f"c{color}: {coords}")
    return "\n".join(lines)


def _bfs_route(grid: list[list[int]], player_bbox: tuple[int, int, int, int] | None,
               targets: list[str] | None = None) -> str:
    """BFS pathfinder on the 5x5 movement grid. Returns turn-by-turn directions.

    targets: list of target types to navigate to, in priority order.
             Options: 'B' (button), 'G' (goal/c9), 'W' (gate/c11).
             Default: ['B', 'G']
    """
    if not grid or not player_bbox:
        return ""
    if targets is None:
        targets = ['B', 'G']

    rows, cols = len(grid), len(grid[0])

    # Build 5x5-aligned grid classification
    grid_rows = (rows - 4) // 5 + 1  # number of 5x5 cells
    grid_cols = (cols - 4) // 5 + 1

    # Find background color
    color_count: dict[int, int] = {}
    for r in range(4, rows - 4):
        for c in range(4, cols - 4):
            color_count[grid[r][c]] = color_count.get(grid[r][c], 0) + 1
    if not color_count:
        return ""
    bg = max(color_count, key=lambda k: color_count[k])

    # Classify each 5x5 cell
    cell_type: dict[tuple[int, int], str] = {}  # (grid_r, grid_c) -> type char
    target_cells: dict[str, list[tuple[int, int]]] = {t: [] for t in targets}

    for gi, gr in enumerate(range(0, rows - 4, 5)):
        for gj, gc in enumerate(range(0, cols - 4, 5)):
            cell_colors: dict[int, int] = {}
            for dr in range(5):
                for dc in range(5):
                    r, c = gr + dr, gc + dc
                    if r < rows and c < cols:
                        v = grid[r][c]
                        cell_colors[v] = cell_colors.get(v, 0) + 1

            # Classify — ONLY c5 (border) and c11 (gate) are walls
            if gr <= player_bbox[0] < gr + 5 and gc <= player_bbox[1] < gc + 5:
                cell_type[(gr, gc)] = 'P'
            elif 5 in cell_colors and cell_colors.get(5, 0) >= 20:
                cell_type[(gr, gc)] = '#'  # border wall
            elif 11 in cell_colors and cell_colors.get(11, 0) >= 5:
                cell_type[(gr, gc)] = 'W'
                if 'W' in target_cells:
                    target_cells['W'].append((gr, gc))
            elif (1 in cell_colors and cell_colors.get(1, 0) >= 2 and 0 in cell_colors
                  and cell_colors.get(3, 0) >= cell_colors.get(0, 0)):
                cell_type[(gr, gc)] = 'B'
                if 'B' in target_cells:
                    target_cells['B'].append((gr, gc))
            elif 9 in cell_colors and cell_colors.get(9, 0) >= 5:
                cell_type[(gr, gc)] = 'G'
                if 'G' in target_cells:
                    target_cells['G'].append((gr, gc))
            else:
                cell_type[(gr, gc)] = '.'  # default walkable (c4 background, etc.)

    # Find player cell
    player_cell = None
    for (gr, gc), t in cell_type.items():
        if t == 'P':
            player_cell = (gr, gc)
            break
    if not player_cell:
        return ""

    # Find first reachable target in priority order
    dest = None
    dest_type = None
    for ttype in targets:
        if target_cells.get(ttype):
            dest_type = ttype
            break
    if not dest_type:
        return ""

    # BFS from player to any target of dest_type
    from collections import deque
    walkable = {'.', 'P', 'B', 'G', 'W'}  # can walk through any non-wall
    queue: deque[tuple[tuple[int, int], list[tuple[int, int]]]] = deque()
    queue.append((player_cell, [player_cell]))
    visited = {player_cell}

    directions = [(-5, 0, 'UP', 'ACTION1'), (5, 0, 'DOWN', 'ACTION2'),
                  (0, -5, 'LEFT', 'ACTION3'), (0, 5, 'RIGHT', 'ACTION4')]

    found_path: list[tuple[int, int]] | None = None
    found_dest: tuple[int, int] | None = None

    while queue:
        pos, path = queue.popleft()

        # Check if we reached a target
        if pos != player_cell and cell_type.get(pos) == dest_type:
            found_path = path
            found_dest = pos
            break

        for dr, dc, _, _ in directions:
            nr, nc = pos[0] + dr, pos[1] + dc
            npos = (nr, nc)
            if npos in visited:
                continue
            if npos not in cell_type:
                continue
            if cell_type[npos] in walkable:
                visited.add(npos)
                queue.append((npos, path + [npos]))

    if not found_path or not found_dest:
        return f"⚠️ No path found from ({player_cell[0]},{player_cell[1]}) to any {dest_type}"

    # Convert path to action sequence
    actions = []
    for i in range(1, len(found_path)):
        pr, pc = found_path[i - 1]
        nr, nc = found_path[i]
        dr, dc = nr - pr, nc - pc
        for ddr, ddc, name, action in directions:
            if dr == ddr and dc == ddc:
                actions.append((action, name))
                break

    # Compress: group consecutive same actions
    compressed = []
    if actions:
        curr_action, curr_name = actions[0]
        count = 1
        for action, name in actions[1:]:
            if action == curr_action:
                count += 1
            else:
                compressed.append(f"{curr_name}x{count}" if count > 1 else curr_name)
                curr_action, curr_name = action, name
                count = 1
        compressed.append(f"{curr_name}x{count}" if count > 1 else curr_name)

    action_seq = ", ".join(a for a, _ in actions)
    route_desc = " → ".join(compressed)

    next_action = actions[0][0] if actions else "?"
    next_name = actions[0][1] if actions else "?"

    return (
        f"📍 ROUTE to {dest_type} at ({found_dest[0]},{found_dest[1]}): "
        f"{route_desc} ({len(actions)} steps)\n"
        f"▶ NEXT ACTION: {next_action} ({next_name}) — follow this route to reach {dest_type}!\n"
        f"Full sequence: {action_seq}"
    )


def _walkability_map(grid: list[list[int]], player_bbox: tuple[int, int, int, int] | None = None) -> str:
    """Generate a compact walkability map aligned to the 5x5 movement grid.
    Shows what occupies each 5x5 grid cell: '.' = walkable, '#' = wall, 'P' = player,
    'B' = button, 'G' = goal/target, '?' = mixed."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    if rows < 20 or cols < 20:
        return ""

    # Find background color
    color_count: dict[int, int] = {}
    for r in range(4, rows - 4):
        for c in range(4, cols - 4):
            color_count[grid[r][c]] = color_count.get(grid[r][c], 0) + 1
    if not color_count:
        return ""
    bg = max(color_count, key=lambda k: color_count[k])

    # Wall colors (typically 4, 5) and walkable colors (0, 3)
    # We'll determine walkability by checking if the 5x5 cell is mostly one type
    lines = []
    header = "    "
    # Column labels
    for gc in range(0, cols - 4, 5):
        header += f"{gc:3d}"
    lines.append(header)

    for gr in range(0, rows - 4, 5):
        row_str = f"{gr:3d} "
        for gc in range(0, cols - 4, 5):
            # Check what's in this 5x5 cell
            cell_colors: dict[int, int] = {}
            for dr in range(5):
                for dc in range(5):
                    r, c = gr + dr, gc + dc
                    if r < rows and c < cols:
                        v = grid[r][c]
                        cell_colors[v] = cell_colors.get(v, 0) + 1

            # Determine cell type — ONLY c5 (border) and c11 (gate) are walls
            if player_bbox and gr <= player_bbox[0] < gr + 5 and gc <= player_bbox[1] < gc + 5:
                row_str += "  P"
            elif 5 in cell_colors and cell_colors.get(5, 0) >= 20:
                # Mostly c5 = border wall
                row_str += "  #"
            elif 11 in cell_colors and cell_colors.get(11, 0) >= 5:
                row_str += "  W"  # c11 wall/gate
            elif (1 in cell_colors and cell_colors.get(1, 0) >= 2 and 0 in cell_colors
                  and cell_colors.get(3, 0) >= cell_colors.get(0, 0)):
                row_str += "  B"  # Button cross
            elif 9 in cell_colors and cell_colors.get(9, 0) >= 5:
                row_str += "  G"  # Goal/target area
            else:
                row_str += "  ."  # Everything else is walkable (c3, c4, c0, etc.)
        lines.append(row_str)

    return "\n".join(lines)


def _find_player_bbox(grid: list[list[int]]) -> tuple[int, int, int, int] | None:
    """Find the 5x5 player block (top 2 rows c12, bottom 3 rows c9). Returns (r, c, r+5, c+5) or None."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    for r in range(4, rows - 8):
        for c in range(4, cols - 8):
            # Check top-left 2x5 = c12, bottom 3x5 = c9
            if grid[r][c] == 12 and grid[r+2][c] == 9:
                ok = True
                for dr in range(2):
                    for dc in range(5):
                        if grid[r + dr][c + dc] != 12:
                            ok = False; break
                    if not ok: break
                if ok:
                    for dr in range(2, 5):
                        for dc in range(5):
                            if grid[r + dr][c + dc] != 9:
                                ok = False; break
                        if not ok: break
                if ok:
                    return (r, c, r + 5, c + 5)
    return None


def _extract_block_pattern(grid: list[list[int]], r0: int, c0: int, rows: int, cols: int, block_size: int, target_color: int) -> str:
    """Extract a logical NxM pattern from a region by grouping block_size x block_size sub-blocks.
    Returns a string like 'X.X / ..X / XXX' where X = target_color present, . = absent."""
    logical_rows = rows // block_size
    logical_cols = cols // block_size
    pattern_rows = []
    for lr in range(logical_rows):
        row_str = ""
        for lc in range(logical_cols):
            # Check if any cell in this sub-block is the target color
            found = False
            for dr in range(block_size):
                for dc in range(block_size):
                    r, c = r0 + lr * block_size + dr, c0 + lc * block_size + dc
                    if 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] == target_color:
                        found = True
                        break
                if found:
                    break
            row_str += "X" if found else "."
        pattern_rows.append(row_str)
    return " / ".join(pattern_rows)


def _find_all_small_patterns(grid: list[list[int]], exclude_border: int = 4) -> list[tuple[str, int, int, int, int, str]]:
    """Find all distinct small colored regions (3-9 cells of same non-bg color in a compact area).
    Returns list of (pattern_str, row, col, height, width, color)."""
    rows_n, cols_n = len(grid), len(grid[0]) if grid else 0
    r_lo, r_hi = exclude_border, rows_n - exclude_border
    c_lo, c_hi = exclude_border, cols_n - exclude_border

    # Find background color
    color_count: dict[int, int] = {}
    for r in range(r_lo, r_hi):
        for c in range(c_lo, c_hi):
            v = grid[r][c]
            color_count[v] = color_count.get(v, 0) + 1
    if not color_count:
        return []
    bg = max(color_count, key=lambda k: color_count[k])

    # Find connected clusters of same non-bg color
    visited: set[tuple[int, int]] = set()
    results = []

    for r in range(r_lo, r_hi):
        for c in range(c_lo, c_hi):
            if (r, c) in visited or grid[r][c] == bg:
                continue
            color = grid[r][c]
            # BFS to find cluster
            cluster = []
            queue = [(r, c)]
            visited.add((r, c))
            while queue:
                cr, cc = queue.pop(0)
                cluster.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if r_lo <= nr < r_hi and c_lo <= nc < c_hi and (nr, nc) not in visited and grid[nr][nc] == color:
                        visited.add((nr, nc))
                        queue.append((nr, nc))

            if len(cluster) < 3 or len(cluster) > 50:
                continue

            min_r = min(cr for cr, _ in cluster)
            max_r = max(cr for cr, _ in cluster)
            min_c = min(cc for _, cc in cluster)
            max_c = max(cc for _, cc in cluster)
            h, w = max_r - min_r + 1, max_c - min_c + 1

            # Only small patterns (≤6x6)
            if h > 6 or w > 6:
                continue

            # Build pattern string
            pattern_rows = []
            for pr in range(min_r, max_r + 1):
                row_str = ""
                for pc in range(min_c, max_c + 1):
                    row_str += "X" if grid[pr][pc] == color else "."
                pattern_rows.append(row_str)
            pattern = " / ".join(pattern_rows)
            results.append((pattern, min_r, min_c, h, w, f"c{color}"))

    return results


def _cluster_changes(change_cells: list[tuple[int, int, int, int]], gap: int = 5) -> list[list[tuple[int, int, int, int]]]:
    """Cluster world changes into separate spatial regions. Cells within `gap` pixels are grouped."""
    if not change_cells:
        return []
    # Simple clustering: group by proximity
    clusters: list[list[tuple[int, int, int, int]]] = []
    remaining = list(change_cells)
    while remaining:
        cluster = [remaining.pop(0)]
        changed = True
        while changed:
            changed = False
            new_remaining = []
            for cell in remaining:
                r, c = cell[0], cell[1]
                near = any(abs(r - cr) <= gap and abs(c - cc) <= gap for cr, cc, _, _ in cluster)
                if near:
                    cluster.append(cell)
                    changed = True
                else:
                    new_remaining.append(cell)
            remaining = new_remaining
        if len(cluster) >= 2:  # Only meaningful clusters
            clusters.append(cluster)
    return clusters


def _analyze_world_changes(prev: list[list[int]], curr: list[list[int]],
                           world_change_cells: list[tuple[int, int, int, int]]) -> str:
    """Analyze remote world changes: cluster into regions, extract patterns, compare to targets."""
    if not world_change_cells:
        return ""

    clusters = _cluster_changes(world_change_cells)
    if not clusters:
        return ""

    all_parts = []
    all_patterns = None  # Lazy-compute once

    for i, cluster in enumerate(clusters):
        rs = [r for r, c, _, _ in cluster]
        cs = [c for r, c, _, _ in cluster]
        min_r, max_r = min(rs), max(rs)
        min_c, max_c = min(cs), max(cs)

        # Expand bounding box to include the full colored region (not just changed cells)
        involved_colors: set[int] = set()
        for _, _, ov, nv in cluster:
            involved_colors.add(ov)
            involved_colors.add(nv)

        # Find bg color
        bg_count: dict[int, int] = {}
        grid_rows, grid_cols = len(curr), len(curr[0])
        for r in range(4, grid_rows - 4):
            for c in range(4, grid_cols - 4):
                bg_count[curr[r][c]] = bg_count.get(curr[r][c], 0) + 1
        bg = max(bg_count, key=lambda k: bg_count[k]) if bg_count else 0
        involved_colors.discard(bg)

        # Iteratively expand bbox to include adjacent cells of involved colors
        expanded = True
        while expanded:
            expanded = False
            scan_r0 = max(0, min_r - 2)
            scan_r1 = min(grid_rows, max_r + 3)
            scan_c0 = max(0, min_c - 2)
            scan_c1 = min(grid_cols, max_c + 3)
            for r in range(scan_r0, scan_r1):
                for c in range(scan_c0, scan_c1):
                    if curr[r][c] in involved_colors:
                        if r < min_r or r > max_r or c < min_c or c > max_c:
                            min_r = min(min_r, r)
                            max_r = max(max_r, r)
                            min_c = min(min_c, c)
                            max_c = max(max_c, c)
                            expanded = True

        h, w = max_r - min_r + 1, max_c - min_c + 1
        parts = [f"Region {i+1}: ({min_r},{min_c})-({max_r},{max_c}) [{h}x{w}], {len(cluster)} cells changed"]

        # Find colors in the expanded region of the CURRENT grid
        region_colors: dict[int, int] = {}
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                v = curr[r][c]
                region_colors[v] = region_colors.get(v, 0) + 1

        if not region_colors:
            all_parts.extend(parts)
            continue

        # Try block sizes 2x2 then 1x1 for pattern extraction
        found_pattern = False
        for block_size in [2, 1]:
            if h % block_size != 0 or w % block_size != 0:
                continue
            logical_h, logical_w = h // block_size, w // block_size
            if logical_h > 5 or logical_w > 5 or logical_h < 2 or logical_w < 2:
                continue

            for color in sorted(region_colors, key=lambda k: region_colors[k], reverse=True):
                if region_colors[color] < 3 or color == bg:
                    continue
                pattern = _extract_block_pattern(curr, min_r, min_c, h, w, block_size, color)
                if "X" not in pattern or "." not in pattern:
                    continue

                parts.append(f"  c{color} pattern ({logical_h}x{logical_w} logical, {block_size}x{block_size} blocks): {pattern}")

                # Lazy-compute all small patterns once
                if all_patterns is None:
                    all_patterns = _find_all_small_patterns(curr)

                # Compare to similar-sized patterns elsewhere
                for p_str, p_r, p_c, p_h, p_w, p_color in all_patterns:
                    if p_h == logical_h and p_w == logical_w:
                        if abs(p_r - min_r) <= h and abs(p_c - min_c) <= w:
                            continue
                        match = "✅ MATCH!" if p_str == pattern else "❌ no match"
                        parts.append(f"  → Compare {p_color} at ({p_r},{p_c}): {p_str} — {match}")

                found_pattern = True
                break
            if found_pattern:
                break

        all_parts.extend(parts)

    return "\n".join(all_parts)


def _grid_diff(prev: list[list[int]], curr: list[list[int]], exclude_border: int = 4) -> str:
    """Show cells that changed, separating player movement from world/remote changes."""
    rows, cols = len(prev), len(prev[0]) if prev else 0
    r_lo, r_hi = exclude_border, rows - exclude_border
    c_lo, c_hi = exclude_border, cols - exclude_border

    # Find player bounding boxes in both frames
    prev_player = _find_player_bbox(prev)
    curr_player = _find_player_bbox(curr)

    # Collect player-area cells (union of old + new player bbox, with margin)
    player_cells: set[tuple[int, int]] = set()
    for bbox in (prev_player, curr_player):
        if bbox:
            pr, pc, pr2, pc2 = bbox
            for r in range(max(r_lo, pr - 1), min(r_hi, pr2 + 1)):
                for c in range(max(c_lo, pc - 1), min(c_hi, pc2 + 1)):
                    player_cells.add((r, c))

    # Categorize changes
    player_changes = []
    raw_world_changes = []  # (r, c, old, new)
    for r in range(r_lo, r_hi):
        for c in range(c_lo, c_hi):
            pv, cv = prev[r][c], curr[r][c]
            if pv != cv:
                if (r, c) in player_cells:
                    player_changes.append(f"({r},{c}):{pv}→{cv}")
                else:
                    raw_world_changes.append((r, c, pv, cv))

    # --- Noise filter: discard isolated single-pixel changes ---
    # A real game-state change involves clusters of pixels, not lone scattered ones.
    changed_set = {(r, c) for r, c, _, _ in raw_world_changes}
    world_changes = []
    for r, c, ov, nv in raw_world_changes:
        # Check if any neighbor (8-connected) also changed
        has_neighbor = any(
            (r + dr, c + dc) in changed_set
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)
        )
        if has_neighbor or len(raw_world_changes) <= 3:
            # Keep clustered changes, or keep all if very few total
            world_changes.append((r, c, ov, nv))
    # If we filtered everything out, report as noise
    if raw_world_changes and not world_changes:
        return "No change (minor pixel noise filtered)."

    if not player_changes and not world_changes:
        return "No change (only border/timer changed)."

    parts = []

    # Player movement summary (compact)
    if player_changes:
        if prev_player and curr_player:
            dr = curr_player[0] - prev_player[0]
            dc = curr_player[1] - prev_player[1]
            parts.append(f"Player moved ({prev_player[0]},{prev_player[1]})→({curr_player[0]},{curr_player[1]}) [Δr={dr},Δc={dc}]")
        else:
            parts.append(f"Player area: {len(player_changes)} cells changed")

    # World/remote changes (HIGHLIGHTED — these are the key discoveries)
    if world_changes:
        change_strs = [f"({r},{c}):{ov}→{nv}" for r, c, ov, nv in world_changes]
        if len(world_changes) > 40:
            # Group by region
            regions: dict[str, list[str]] = {}
            for entry in change_strs:
                coord = entry.split(":")[0]
                r_val = int(coord.strip("(").split(",")[0])
                c_val = int(coord.split(",")[1].strip(")"))
                region_key = f"rows {(r_val // 10) * 10}-{(r_val // 10) * 10 + 9}, cols {(c_val // 10) * 10}-{(c_val // 10) * 10 + 9}"
                regions.setdefault(region_key, []).append(entry)
            region_lines = [f"  {k}: {len(v)} cells" for k, v in sorted(regions.items())]
            parts.append(f"🌍 WORLD CHANGED — {len(world_changes)} cells changed AWAY from player:\n" + "\n".join(region_lines))
        else:
            parts.append(f"🌍 WORLD CHANGED — {len(world_changes)} cells (not player movement): " + ", ".join(change_strs))

        # Auto-analyze patterns in changed region
        analysis = _analyze_world_changes(prev, curr, world_changes)
        if analysis:
            parts.append(f"📐 PATTERN ANALYSIS:\n{analysis}")

    return "\n".join(parts)


class ArcPlayer:
    """ARC game agent with structured file memory."""

    def __init__(
        self,
        game_id: str,
        arc_env: Any,
        arcade: Any,
        model: str = "",
        scorecard_id: str = "",
        shortcut: bool = False,
    ):
        self.game_id = game_id
        self.arc_env = arc_env
        self.arcade = arcade
        self.model = model or os.getenv("ARC_AGI_MODEL", "google/gemini-3.1-pro-preview")
        self.scorecard_id = scorecard_id

        # Memory (level-aware)
        self.memory = MemoryManager(game_id, base_dir=Path(__file__).parent / "memory", level=1)

        # Game state
        self.frames: list[Any] = []
        self.messages: list[dict[str, Any]] = []
        self.step_count = 0
        self.retry_count = 0
        self.current_steps: list[dict[str, Any]] = []
        self.current_level = 1  # Track current level for shortcuts
        self._last_score_step = 0  # Step when score last changed (for stuck detection)

        # Periodic meta-summary
        self._last_meta_summary_step = 0

        # Hierarchical planning: strategic plan that persists across steps
        self._consecutive_blocked = 0  # Track consecutive blocked actions

        # Score review gate (enables promote_to_shared tool)
        self._in_score_review = False
        self._score_review_done = False

        # Evidence tool usage tracking
        self._last_evidence_step = 0  # Last step where confirm/contradict was called

        # Grid map snapshot history: list of (step, minimap)
        self._map_snapshots: list[tuple[int, list[list[str]]]] = []

        # Exploration tree
        tree_dir = Path(__file__).parent / "memory" / game_id
        self.tree = ExplorationTree(save_dir=tree_dir)

        # Load skills (universal + per-game per-level)
        self._skill_base_dir = Path(__file__).parent / "skills" / "arc-game-playing"
        self._load_skill()

        # LLM client
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self._client = OpenAIClient(api_key=api_key, base_url=base_url, timeout=120)

        # Shortcuts: replay solved levels without LLM
        self._shortcut_enabled = shortcut
        self._shortcut_file = Path(__file__).parent / "memory" / game_id / "shortcuts.json"
        self._shortcuts: dict[str, list[str]] = self._load_shortcuts()

        # Recording
        from arc.recorder import Recorder
        self.recorder = Recorder(prefix=f"{game_id}.arc-player.{self.model.replace('/', '-')}")
        logger.info("Recording to %s", self.recorder.filename)

        # Message-level JSONL log (every LLM call: request + response)
        self._msg_log_path = Path(self.recorder.filename).with_suffix(".messages.jsonl")
        logger.info("Message log: %s", self._msg_log_path)

        # Stats
        self.total_tokens = 0
        self.llm_calls = 0

    # ── Shortcuts ─────────────────────────────────────────────────────

    def _load_shortcuts(self) -> dict[str, list[str]]:
        """Load saved winning action sequences per level."""
        try:
            if self._shortcut_file.is_file():
                data = json.loads(self._shortcut_file.read_text(encoding="utf-8"))
                logger.info("Shortcuts loaded: %d levels solved", len(data))
                return data
        except Exception as e:
            logger.warning("Failed to load shortcuts: %s", e)
        return {}

    def _save_shortcut(self, level: int, actions: list[str]) -> None:
        """Save winning action sequence (only if shorter than existing)."""
        existing = self._shortcuts.get(str(level))
        if existing and len(existing) <= len(actions):
            return
        self._shortcuts[str(level)] = actions
        try:
            self._shortcut_file.parent.mkdir(parents=True, exist_ok=True)
            self._shortcut_file.write_text(
                json.dumps(self._shortcuts, indent=2), encoding="utf-8",
            )
            logger.info("Shortcut saved: level %d → %d actions", level, len(actions))
        except Exception as e:
            logger.warning("Failed to save shortcut: %s", e)

    def _replay_shortcut(self, level: int) -> bool:
        """Replay saved winning path. Returns True if level completed."""
        actions = self._shortcuts.get(str(level))
        if not actions:
            return False
        logger.info("SHORTCUT: replaying %d actions for level %d", len(actions), level)
        for i, action_name in enumerate(actions):
            frame = self.frames[-1]
            if frame.state is GameState.WIN:
                return True
            if frame.state is GameState.GAME_OVER:
                logger.warning("SHORTCUT: game_over during replay at step %d", i)
                return False
            self._execute_game_action(action_name, record=True)
            curr_score = self.frames[-1].levels_completed if self.frames else 0
            if curr_score > level - 1:
                logger.info("SHORTCUT: level %d completed at step %d/%d", level, i + 1, len(actions))
                return True
        logger.warning("SHORTCUT: replay failed for level %d after %d actions", level, len(actions))
        return False

    # ── Main Loop ─────────────────────────────────────────────────────

    def main(self) -> None:
        max_retries = int(os.getenv("ARC_MAX_RETRIES", "5"))
        logger.info("Starting ARC player for game %s (model: %s)", self.game_id, self.model)

        for attempt in range(max_retries):
            self.retry_count = attempt
            result = self._play_episode()

            if result == "win":
                logger.info("Game won after %d attempts!", attempt + 1)
                self._generate_live_video()
                break
            elif result in ("game_over", "max_actions"):
                logger.info("Episode ended: %s (attempt %d/%d)", result, attempt + 1, max_retries)
                self._generate_live_video()
                self._save_postmortem(result)
                self._force_failure_analysis(result)
                self._update_game_facts()
                self._reset_state()
            else:
                logger.info("Episode ended: %s", result)
                break

        self._log_stats()

    def _play_episode(self) -> str:
        """Play one full episode."""
        # Reset game
        frame = self._do_reset()
        if not frame:
            return "error"

        self.frames = [frame]
        self.current_steps = []
        self.step_count = 0
        score_at_start = frame.levels_completed
        self.current_level = score_at_start + 1
        level_start_step = 0  # Track where current level started (for shortcut saving)

        # Replay shortcuts for already-solved levels
        if self._shortcut_enabled:
            level = score_at_start + 1
            while str(level) in self._shortcuts:
                if not self._replay_shortcut(level):
                    logger.warning("Shortcut replay failed at level %d, switching to LLM", level)
                    break
                level += 1
                self.current_level = level
                self.memory.set_level(level)
                self._load_skill()  # Reload skill for new level
                self._last_score_step = self.step_count  # Reset stuck counter after shortcut
                level_start_step = self.step_count

            latest = self.frames[-1] if self.frames else None
            if latest and latest.state is GameState.WIN:
                return "win"

        # Save initial grid map for this level
        self._save_grid_map()

        max_actions = int(os.getenv("ARC_MAX_ACTIONS", "300"))
        consecutive_failures = 0

        while True:
            latest = self.frames[-1]

            # Terminal checks
            if latest.state is GameState.WIN:
                return "win"
            if latest.state is GameState.GAME_OVER:
                return "game_over"
            if max_actions and self.step_count >= max_actions:
                return "max_actions"

            prev_score = latest.levels_completed

            # After too many consecutive failures, force a random game action
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                import random
                forced = random.choice(["ACTION1", "ACTION2", "ACTION3", "ACTION4"])
                logger.warning("Forcing random action %s after %d consecutive LLM failures", forced, consecutive_failures)
                self._execute_game_action(forced)
                # Add complete assistant→tool pair to message history
                forced_tc_id = f"forced_{self.step_count}"
                self.messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": forced_tc_id,
                        "type": "function",
                        "function": {"name": forced, "arguments": "{}"},
                    }],
                })
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": forced_tc_id,
                    "content": "Forced action executed.",
                })
                consecutive_failures = 0
                continue

            # Navigation autopilot DISABLED — let LLM decide all routes
            # (BFS had incorrect walkability: c12/c9 treated as passable)

            # Build observation and get LLM decision
            obs = self._build_observation()
            took_action = self._llm_step(obs)

            # Turn off score review gate only after agent has done at least one
            # review action (write_memory/promote/update_skill). If it jumped
            # straight to a game action, keep review on for one more step.
            if self._in_score_review:
                if took_action and not self._score_review_done:
                    # Agent skipped review — give it one more chance
                    self._score_review_done = False
                else:
                    self._in_score_review = False
                    self._score_review_done = False

            if took_action:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning("LLM failed to produce game action (%d consecutive)", consecutive_failures)

            # Generate video every 5 steps
            if self.step_count > 0 and self.step_count % 5 == 0:
                self._generate_live_video()

            # Update grid map every 20 steps
            if self.step_count > 0 and self.step_count % 20 == 0:
                self._save_grid_map()

            # Save exploration tree periodically
            if self.step_count > 0 and self.step_count % 10 == 0:
                self.tree.save()

            # Check for level completion → save shortcut + review + update memory level
            curr_score = self.frames[-1].levels_completed if self.frames else 0
            if curr_score > prev_score:
                # Extract action sequence for the completed level
                level_actions = [
                    s["action"] for s in self.current_steps[level_start_step:]
                ]
                self._save_shortcut(self.current_level, level_actions)
                self.current_level = curr_score + 1
                self.memory.set_level(self.current_level)
                self._load_skill()  # Reload skill for new level
                self._last_score_step = self.step_count  # Reset stuck counter
                level_start_step = len(self.current_steps)
                logger.info("Level up! Now on level %d", self.current_level)
                # Save grid map for new level
                self._save_grid_map()
                # Force agent to reflect on what caused the score
                self._force_score_review()

            # Trim messages to stay within window
            self._trim_messages()

    # ── LLM Step ──────────────────────────────────────────────────────

    def _llm_step(self, observation: str) -> bool:
        """Single step: push observation → call LLM → process tools.

        Returns True if a game action was executed.

        Gemini message protocol:
        - Each assistant tool_call gets exactly ONE tool response
        - Tool responses must immediately follow their assistant message
        - Observations are delivered via a synthetic "observe" assistant+tool pair
        """
        # Deliver observation as a user message.
        # This avoids Gemini's strict function_call→function_response pairing
        # issues. Each tool_call gets exactly one tool response (added during
        # processing), and observations are delivered cleanly as user messages.
        self.messages.append({
            "role": "user",
            "content": observation,
        })

        for round_idx in range(MAX_TOOL_ROUNDS):
            msg_count_before = len(self.messages)
            response = self._call_llm()
            if not response or not response.choices:
                if len(self.messages) > msg_count_before:
                    self.messages = self.messages[:msg_count_before]
                return False

            message = response.choices[0].message
            if not message.tool_calls:
                # Model returned text only (reasoning) without tool calls.
                # Save its reasoning to history, then loop to get a tool call.
                if message.content:
                    logger.info("LLM reasoning (no tool call): %s", message.content[:120])
                    self.messages.append({"role": "assistant", "content": message.content})
                    self.messages.append({"role": "user", "content": "Now call a tool — either a game ACTION or a memory tool."})
                    continue
                logger.warning("LLM returned no tool calls and no content")
                return False

            # Add assistant message to history
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if message.content:
                assistant_msg["content"] = message.content
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in message.tool_calls
            ]
            self.messages.append(assistant_msg)

            # Process ALL tool calls. Each gets exactly one tool response.
            game_action_taken = False

            for tc in message.tool_calls:
                name = tc.function.name
                args_str = tc.function.arguments or "{}"

                if name in GAME_ACTIONS:
                    ok = self._execute_game_action(name, args_str)
                    if ok:
                        game_action_taken = True
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": "Action executed successfully.",
                        })
                    else:
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"ERROR: {name} failed (server error). Try a different action.",
                        })
                else:
                    logger.info("Non-game tool: %s(%s)", name, args_str[:80] if args_str else "")
                    result = self._handle_tool(name, args_str)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            if game_action_taken:
                return True

            steps_since_score = self.step_count - self._last_score_step
            is_stuck = steps_since_score >= STUCK_THRESHOLD

            # When stuck: force hypothesis on round 4 by REPLACING tool output
            if is_stuck and round_idx == 2 and self.messages and self.messages[-1]["role"] == "tool":
                logger.info("FORCING hypothesis prompt at round %d (stuck %d steps)", round_idx, steps_since_score)
                self.messages[-1]["content"] = (
                    "⛔ SYSTEM OVERRIDE — You are not making progress. "
                    f"Stuck for {steps_since_score} steps without scoring.\n\n"
                    "You MUST do ALL of these in your NEXT response:\n"
                    "1. `list_memory(folder='hypotheses')` — see your hypotheses\n"
                    "2. `contradict(filename='action_mappings.md', observation='Step N: ...')` — "
                    "contradict at least ONE wrong hypothesis with specific evidence from recent steps\n"
                    "3. `confirm(filename='...', observation='Step N: ...')` — "
                    "confirm at least ONE correct hypothesis with specific evidence\n"
                    "4. `write_memory(folder='hypotheses', filename='new_approach.md', content='...')` — "
                    "write a FUNDAMENTALLY DIFFERENT hypothesis\n"
                    "5. Call a GAME ACTION to test it\n\n"
                    "You have been taking actions without updating evidence. "
                    "Use confirm/contradict NOW to separate what works from what doesn't."
                )

            # Nudge on last allowed round
            if round_idx == MAX_TOOL_ROUNDS - 1 and self.messages and self.messages[-1]["role"] == "tool":
                self.messages[-1]["content"] += (
                    "\n\n⚠️ You MUST call a game action NOW (ACTION1-ACTION6). "
                    "Save discoveries with write_memory, then MOVE."
                )

        return False

    # ── Tool Handling ─────────────────────────────────────────────────

    def _handle_tool(self, name: str, args_str: str) -> str:
        """Handle non-game-action tool calls."""
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            return "Error: invalid JSON."

        if name == "list_memory":
            return self.memory.list_files(args.get("folder", ""), scope=args.get("scope"))
        elif name == "read_memory":
            return self.memory.read_file(args.get("folder", ""), args.get("filename", ""), scope=args.get("scope"))
        elif name == "write_memory":
            result = self.memory.write_file(
                args.get("folder", ""),
                args.get("filename", ""),
                args.get("content", ""),
                scope=args.get("scope"),
            )
            # Attach artifact to current tree node
            folder = args.get("folder", "")
            filename = args.get("filename", "")
            art_type = {"discoveries": "discovery", "hypotheses": "hypothesis",
                        "summaries": "summary"}.get(folder)
            if art_type:
                self.tree.attach_artifact(art_type, filename)
            # Mark score review as done if writing summaries during review
            if self._in_score_review and folder == "summaries":
                self._score_review_done = True
            return result
        elif name == "confirm":
            result = self.memory.confirm(args.get("filename", ""), args.get("observation", ""), scope=args.get("scope"))
            if not result.startswith("SKIPPED"):
                self._last_evidence_step = self.step_count
            # Attach as proof
            self.tree.attach_artifact("proof", f"✓{args.get('filename', '')}")
            return result
        elif name == "contradict":
            self._last_evidence_step = self.step_count
            result = self.memory.contradict(args.get("filename", ""), args.get("observation", ""), scope=args.get("scope"))
            self.tree.attach_artifact("proof", f"✗{args.get('filename', '')}")
            return result
        elif name == "promote_to_shared":
            if not self._in_score_review:
                return (
                    "Error: promote_to_shared is only available during score/level-up review. "
                    "It will be enabled when you score and advance to a new level."
                )
            self._score_review_done = True
            return self.memory.promote_to_shared(
                args.get("folder", ""),
                args.get("filename", ""),
                source_scope=args.get("source_scope"),
            )
        elif name == "update_plan":
            return self._handle_update_plan(args.get("goal", ""), args.get("route", ""), args.get("next_actions", ""))
        elif name == "update_skill":
            if self._in_score_review:
                self._score_review_done = True
            return self._handle_update_skill(args.get("content", ""))
        elif name == "view_tree":
            return self._handle_view_tree(args)
        elif name == "view_node":
            return self._handle_view_node(args)
        else:
            return f"Unknown tool: {name}. Valid: ACTION1-6, list/read/write_memory, confirm, contradict, update_plan, promote_to_shared, update_skill, view_tree, view_node."

    def _handle_view_tree(self, args: dict) -> str:
        """Handle view_tree tool: show branch summary or subtree."""
        mode = args.get("mode", "branch")
        count = int(args.get("count", 20))
        if mode == "branch":
            return self.tree.get_branch_summary(last_n=count)
        elif mode == "world_changes":
            nodes = self.tree.find_world_change_nodes(last_n=count)
            if not nodes:
                return "No world-change events found."
            return "\n".join(n.compact_str() for n in nodes)
        elif mode == "scores":
            nodes = self.tree.find_score_nodes()
            if not nodes:
                return "No scoring events found."
            return "\n".join(n.full_str() for n in nodes)
        elif mode == "search":
            query = args.get("query", "")
            if not query:
                return "Error: 'query' required for search mode."
            nodes = self.tree.search_nodes(query, max_results=count)
            if not nodes:
                return f"No nodes matching '{query}'."
            return "\n".join(n.compact_str() for n in nodes)
        elif mode == "stats":
            return self.tree.stats()
        else:
            return f"Unknown mode '{mode}'. Use: branch, world_changes, scores, search, stats."

    def _handle_view_node(self, args: dict) -> str:
        """Handle view_node tool: show full detail of a specific node."""
        node_id = args.get("node_id", "")
        if not node_id:
            return "Error: 'node_id' required."
        node = self.tree.get_node(node_id)
        if not node:
            return f"Node '{node_id}' not found. Use view_tree to see available nodes."
        result = node.full_str()
        # Also show subtree if it has children
        if node.children:
            result += f"\n\nChildren ({len(node.children)}):\n"
            result += self.tree.get_subtree_str(node_id, depth=2)
        return result

    def _get_current_plan(self) -> str | None:
        """Read current strategic plan from summaries/current_plan.md."""
        content = self.memory.read_file("summaries", "current_plan.md")
        if content.startswith("Error:"):
            return None
        return content

    def _handle_update_plan(self, goal: str, route: str, next_actions: str) -> str:
        """Update the strategic plan. This is the agent's high-level plan for what to do."""
        if not goal:
            return "Error: 'goal' is required. What are you trying to achieve?"

        content = (
            "---\n"
            f'name: "Current Plan"\n'
            f'description: "Strategic plan for level {self.current_level}"\n'
            "---\n\n"
            f"## Goal\n{goal}\n\n"
            f"## Route\n{route}\n\n"
            f"## Next Actions\n{next_actions}\n"
        )
        result = self.memory.write_file("summaries", "current_plan.md", content)
        logger.info("Plan updated: goal=%s", goal[:60])
        return f"Plan updated. Now EXECUTE it — take a game action."

    def _record_map_snapshot(self) -> None:
        """Record current grid as a minimap snapshot."""
        latest = self.frames[-1] if self.frames else None
        if not latest or not latest.frame:
            return
        minimap = _grid_to_minimap(latest.frame[0])
        if minimap:
            self._map_snapshots.append((self.step_count, minimap))
            # Trim to max
            if len(self._map_snapshots) > MAX_MAP_SNAPSHOTS:
                self._map_snapshots = self._map_snapshots[-MAX_MAP_SNAPSHOTS:]

    def _save_grid_map(self) -> None:
        """Save Fibonacci-spaced grid map history to discoveries/grid-map.md.

        Shows 10 snapshots at Fibonacci intervals: steps -0, -1, -2, -3, -5, -8, -13, -21, -34, -55.
        Recent maps are dense (every step), older maps are sparse.
        """
        # Record current snapshot first
        self._record_map_snapshot()

        if not self._map_snapshots:
            return

        map_text = _render_map_history(self._map_snapshots)
        n_snaps = min(len(self._map_snapshots), len(FIB_OFFSETS))

        content = (
            f"---\n"
            f"name: \"Grid Map History (step {self.step_count})\"\n"
            f"description: \"{n_snaps} snapshots at Fibonacci intervals, 12x12 overview per snapshot\"\n"
            f"confirmed_count: 0\n"
            f"contradicted_count: 0\n"
            f"---\n\n"
            f"{map_text}\n\n"
            f"Player (c12) = 'C', Walls (c11) = 'B', Background varies.\n"
            f"Compare maps across steps to see what MOVED and what's STATIC.\n"
        )
        self.memory.write_file("discoveries", "grid-map.md", content)
        logger.info("Grid map saved at step %d (%d snapshots, %d shown)", self.step_count, len(self._map_snapshots), n_snaps)

    def _handle_update_skill(self, content: str) -> str:
        """Update agent's supplementary notes (SKILL.agent.md). Base rules are immutable."""
        if not content or len(content.strip()) < 20:
            return "Error: content too short. Must contain meaningful guidance."

        level_dir = self._skill_base_dir / self.game_id / f"level{self.current_level}"
        level_dir.mkdir(parents=True, exist_ok=True)
        skill_path = level_dir / "SKILL.agent.md"
        skill_path.write_text(content, encoding="utf-8")
        self._load_skill()  # Reload combined skill into system prompt
        logger.info("SKILL.agent.md updated for %s/level%d (%d chars)", self.game_id, self.current_level, len(content))
        return (f"Agent notes updated ({len(content)} chars). "
                f"NOTE: The base RULES are immutable — your notes supplement but cannot override them.")

    # ── Game Actions ──────────────────────────────────────────────────

    def _do_reset(self) -> Optional[Any]:
        """Reset game and return first frame."""
        try:
            raw = self.arc_env.step(action=GameAction.RESET, data={}, reasoning={})
            return self._convert_frame(raw)
        except Exception as e:
            logger.error("Reset failed: %s", e)
            return None

    def _try_nav_autopilot(self, grid: list[list[int]]) -> str | None:
        """If BFS route exists to a target, return the next action to take.

        Returns None if:
        - Player is already AT a button/target (let LLM handle interaction)
        - No route found
        - Last autopilot action was blocked (need LLM to replan)
        - World changed (need LLM to analyze)
        """
        player_bbox = _find_player_bbox(grid)
        if not player_bbox:
            return None

        # Don't autopilot if the last action caused a world change
        if (len(self.frames) >= 2 and self.frames[-2].frame):
            diff = _grid_diff(self.frames[-2].frame[0], grid)
            if "🌍 WORLD CHANGED" in diff:
                return None

        # Don't autopilot if last action was blocked (need to rethink)
        if self.current_steps and self.current_steps[-1]["effect"] == "blocked":
            # Only block autopilot after 2+ consecutive blocks
            blocked_count = 0
            for s in reversed(self.current_steps):
                if s["effect"] == "blocked":
                    blocked_count += 1
                else:
                    break
            if blocked_count >= 2:
                return None

        # Check if player is already at a button
        rows, cols = len(grid), len(grid[0])
        pr, pc = player_bbox[0], player_bbox[1]
        # Check the 5x5 cell the player is in for button indicators
        cell_colors: dict[int, int] = {}
        for dr in range(5):
            for dc in range(5):
                r, c = pr + dr, pc + dc
                if r < rows and c < cols:
                    v = grid[r][c]
                    cell_colors[v] = cell_colors.get(v, 0) + 1
        # If player is ON a button (c1+c0 present in same cell), let LLM handle
        if 1 in cell_colors and 0 in cell_colors:
            return None

        # Compute BFS route
        route_str = _bfs_route(grid, player_bbox)
        if not route_str or "No path found" in route_str:
            return None

        # Extract the next action from the route
        import re
        m = re.search(r'NEXT ACTION: (ACTION[1-6])', route_str)
        if m:
            return m.group(1)

        return None

    def _execute_game_action(self, name: str, args_str: str = "{}", record: bool = True) -> bool:
        """Execute a game action and record the step. Returns True if successful."""
        try:
            data = json.loads(args_str) if isinstance(args_str, str) and args_str else {}
        except json.JSONDecodeError:
            data = {}

        action = GameAction[name]

        prev_frame = self.frames[-1] if self.frames else None
        prev_score = prev_frame.levels_completed if prev_frame else 0

        try:
            raw = self.arc_env.step(action=action, data=data, reasoning={})
            frame = self._convert_frame(raw)
        except Exception as e:
            logger.error("Action %s failed: %s", name, e)
            return False

        if frame:
            self.frames.append(frame)
            self.step_count += 1

            curr_score = frame.levels_completed
            # Detect effect (exclude border/timer area)
            effect = "no_change"
            if prev_frame and prev_frame.frame and frame.frame:
                prev_grid = prev_frame.frame[0]
                curr_grid = frame.frame[0]
                inner_changed = False
                for r in range(4, 60):
                    for c in range(4, 60):
                        if prev_grid[r][c] != curr_grid[r][c]:
                            inner_changed = True
                            break
                    if inner_changed:
                        break
                effect = "moved" if inner_changed else "blocked"
            if curr_score > prev_score:
                effect = f"scored +{curr_score - prev_score}"

            # Compute positions and world-change BEFORE storing step
            prev_pos = _find_player_bbox(prev_frame.frame[0]) if prev_frame and prev_frame.frame else None
            curr_pos = _find_player_bbox(frame.frame[0]) if frame.frame else None
            world_changed = False
            if prev_frame and prev_frame.frame and frame.frame:
                diff_str = _grid_diff(prev_frame.frame[0], frame.frame[0])
                world_changed = "🌍 WORLD CHANGED" in diff_str

            self.current_steps.append({
                "action": name,
                "effect": effect,
                "score": curr_score,
                "step": self.step_count,
                "pos": f"({curr_pos[0]},{curr_pos[1]})" if curr_pos else None,
                "world_changed": world_changed,
            })
            logger.info("Step %d: %s → %s (score=%d)", self.step_count, name, effect, curr_score)

            # Add node to exploration tree

            state_desc = f"pos=({prev_pos[0]},{prev_pos[1]})" if prev_pos else "unknown"
            state_desc += f" score={prev_score} level={self.current_level}"
            next_desc = f"pos=({curr_pos[0]},{curr_pos[1]})" if curr_pos else "unknown"
            next_desc += f" score={curr_score}"
            if world_changed:
                next_desc += " 🌍world_changed"

            self.tree.add_node(
                step=self.step_count,
                action=name,
                effect=effect,
                state=state_desc,
                next_state=next_desc,
                score=curr_score,
                level=self.current_level,
                player_pos=(curr_pos[0], curr_pos[1]) if curr_pos else None,
                world_changed=world_changed,
            )

            # Record minimap snapshot for Fibonacci history
            self._record_map_snapshot()

            # Record to JSONL
            if record:
                try:
                    self.recorder.record({
                        "frame": frame.frame,
                        "action": name,
                        "score": curr_score,
                        "state": frame.state.name,
                        "step": self.step_count,
                        "effect": effect,
                    })
                except Exception as e:
                    logger.debug("Recording failed: %s", e)

            return True
        return False

    def _convert_frame(self, raw: Any) -> Optional[Any]:
        """Convert raw frame data to usable format."""
        if raw is None:
            return None
        from arcengine import FrameData
        return FrameData(
            game_id=raw.game_id,
            frame=[arr.tolist() for arr in raw.frame] if raw.frame is not None else [],
            state=raw.state,
            levels_completed=raw.levels_completed,
            win_levels=raw.win_levels,
            guid=raw.guid,
            full_reset=raw.full_reset,
            available_actions=raw.available_actions,
        )

    # ── Skill loading ────────────────────────────────────────────────

    def _load_skill(self) -> None:
        """Load universal skill + base (immutable) + agent notes into self._skill."""
        parts = []

        # Universal skill (always loaded)
        universal = self._skill_base_dir / "SKILL.md"
        if universal.is_file():
            parts.append(universal.read_text(encoding="utf-8"))

        level_dir = self._skill_base_dir / self.game_id / f"level{self.current_level}"

        # Base skill (IMMUTABLE — cannot be overwritten by agent)
        base_skill = level_dir / "SKILL.base.md"
        if base_skill.is_file():
            parts.append(
                f"\n# Level {self.current_level} RULES (IMMUTABLE — follow these exactly)\n"
                + base_skill.read_text(encoding="utf-8")
            )

        # Agent's own notes (written by update_skill, supplementary only)
        agent_skill = level_dir / "SKILL.agent.md"
        if agent_skill.is_file():
            parts.append(
                f"\n# Level {self.current_level} Agent Notes (your own observations)\n"
                + agent_skill.read_text(encoding="utf-8")
            )

        self._skill = "\n\n".join(parts) if parts else ""

    # ── Prompts ───────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """System prompt: skill + game/level context + verified rules + strategy."""
        sections = [self._skill]

        # Game-wide facts (ALWAYS loaded, high priority)
        facts_path = self._skill_base_dir / self.game_id / "FACTS.md"
        if facts_path.is_file():
            facts_content = facts_path.read_text(encoding="utf-8").strip()
            if facts_content:
                sections.append(
                    "## Universal Game Knowledge (CRITICAL — these facts apply to ALL levels)\n" + facts_content
                )

        # Game and level context
        sections.append(
            f"# Context\n"
            f"Game: {self.game_id} | Level: {self.current_level} | Attempt: {self.retry_count + 1}\n\n"
            f"Memory scopes: `current` (this level), `shared` (game-wide, read-only — populated via promote_to_shared after scoring), `levelN` (other levels).\n\n"
            f"**CRITICAL — PERSIST ALL KNOWLEDGE**: Your message history is SHORT and will be compressed. "
            f"ANYTHING you learn MUST be saved to memory or skill files IMMEDIATELY. "
            f"If it's not in memory, it's LOST. Write discoveries, hypotheses, and strategies "
            f"to memory after EVERY significant observation. Don't rely on remembering — WRITE IT DOWN."
        )

        # Current strategic plan — shown prominently
        plan = self._get_current_plan()
        if plan:
            sections.append(f"# YOUR CURRENT PLAN (strategic layer)\n{plan}\n"
                            "Follow this plan. If it's not working, call `update_plan` to revise it "
                            "BEFORE trying more actions.")
        else:
            sections.append(
                "# NO PLAN SET\n"
                "You have no strategic plan. Before taking game actions, call `update_plan` to set:\n"
                "- goal: What are you trying to achieve?\n"
                "- route: How will you get there? (sequence of directions)\n"
                "- next_actions: What are your next 3-5 specific actions?"
            )

        # Grid map — always loaded if available
        grid_map_content = self.memory.read_file("discoveries", "grid-map.md")
        if not grid_map_content.startswith("Error:"):
            sections.append(f"# Current Board Map\n{grid_map_content}")

        # Live memory snapshot — all folders, all counts, always up-to-date
        memory_snapshot = self.memory.get_memory_snapshot()
        if memory_snapshot:
            sections.append(f"# Memory Snapshot (live)\n{memory_snapshot}")

        # Retry context
        if self.retry_count > 0:
            sections.append(
                f"# Attempt {self.retry_count + 1}. Previous attempts failed — try DIFFERENT approach.\n"
                "Use `list_memory` with different scopes to review past findings from this and other levels."
            )

        return "\n\n".join(sections)

    def _build_observation(self) -> str:
        """Build observation from current game state."""
        latest = self.frames[-1] if self.frames else None
        if not latest:
            return "No frame data."

        sections = []

        # Score and state
        score = latest.levels_completed
        bfs_route_str = ""  # computed later, appended at end
        sections.append(f"Game: {self.game_id} | Level: {self.current_level} | Score: {score} | Step: {self.step_count}")

        # Level-up notice
        if self.current_steps and len(self.current_steps) >= 2:
            prev_score = self.current_steps[-2].get("score", 0)
            if score > prev_score:
                sections.append(f"LEVEL UP! Now on level {score + 1}. New layout, same mechanics.")

        # Exploration tree — last 8 nodes so agent can see repetition patterns
        tree_recent = self.tree.render_recent(8)
        if tree_recent and tree_recent != "(no exploration history yet)":
            sections.append(f"📊 Recent exploration:\n{tree_recent}\n"
                            "Use `view_tree` to browse full history, `view_node` to inspect a specific node.")

        # Grid (compact)
        if latest.frame:
            sections.append(f"Grid:\n{_compact_grid(latest.frame[0])}")

            # Walkability map — show on level-up, every 5 steps, or when blocked
            player_bbox = _find_player_bbox(latest.frame[0])
            is_level_up = (self.current_steps and len(self.current_steps) >= 2
                           and self.current_steps[-2].get("score", 0) < score)
            show_nav = (self.step_count <= 1 or self.step_count % 5 == 0 or is_level_up or
                        (self.current_steps and self.current_steps[-1]["effect"] == "blocked"))
            if show_nav:
                walk_map = _walkability_map(latest.frame[0], player_bbox)
                if walk_map:
                    pos_str = f"Player at grid ({player_bbox[0]},{player_bbox[1]}). " if player_bbox else ""
                    sections.append(
                        f"🗺️ NAV MAP (5x5 grid, P=you, B=button, G=goal, #=wall, .=open, W=gate):\n{walk_map}\n"
                        f"{pos_str}Use this map to plan routes. Move through '.' cells to reach B or G.\n"
                        "ACTION1=UP(row-5), ACTION2=DOWN(row+5), ACTION3=LEFT(col-5), ACTION4=RIGHT(col+5)."
                    )
            elif player_bbox:
                sections.append(f"Player position: ({player_bbox[0]},{player_bbox[1]})")

            # BFS route DISABLED — agent chooses its own routes
            bfs_route_str = ""

        # Grid diff with world-change analysis
        if len(self.frames) >= 2 and self.frames[-2].frame and latest.frame:
            diff = _grid_diff(self.frames[-2].frame[0], latest.frame[0])
            last_action = self.current_steps[-1]["action"] if self.current_steps else "RESET"
            sections.append(f"After {last_action}: {diff}")

            # Causation prompt: when world changes happen, prompt agent to think about WHY
            if "🌍 WORLD CHANGED" in diff:
                sections.append(
                    "🧠 CAUSATION ANALYSIS REQUIRED:\n"
                    "The world changed AWAY from your player. This is a CRITICAL clue.\n"
                    "1. WHAT changed? The PATTERN ANALYSIS above shows the simplified logical pattern.\n"
                    "2. WHY did it change? What did you just do? (stepped on button? entered a zone?)\n"
                    "3. COMPARE: The analysis shows pattern comparisons to other shapes on the grid. Do any MATCH?\n"
                    "4. CYCLE: Try the same action again — does the pattern cycle? How many states?\n"
                    "5. SCORING HYPOTHESIS: When the remote pattern MATCHES a target pattern, that match "
                    "itself may BE how you score. You may NOT need to walk anywhere else — the pattern "
                    "match could directly trigger scoring or unlock the next step.\n"
                    "→ UPDATE (don't create new files): `write_memory(folder='discoveries', filename='remote-change-analysis.md', ...)`\n"
                    "→ Create/update hypothesis: `write_memory(folder='hypotheses', filename='pattern-match-scoring.md', ...)`"
                )

        # Track consecutive blocked actions
        if self.current_steps and self.current_steps[-1]["effect"] == "blocked":
            self._consecutive_blocked += 1
            last_act = self.current_steps[-1]["action"]
            if self._consecutive_blocked >= 2:
                sections.append(
                    f"🚨 {self._consecutive_blocked} BLOCKED in a row! STOP. "
                    f"Look at the 📍 ROUTE above — your NEXT action MUST be the one shown there."
                )
            else:
                sections.append(f"⚠️ {last_act} was BLOCKED — wall or obstacle. Try a different direction.")
        else:
            self._consecutive_blocked = 0

        # Evidence starvation warning — agent hasn't used confirm/contradict recently
        steps_without_evidence = self.step_count - self._last_evidence_step
        if steps_without_evidence >= 5 and self.step_count > 5:
            sections.append(
                f"⚠️ WARNING: You have taken {steps_without_evidence} actions without calling `confirm` or `contradict`. "
                "You are WASTING steps! Your hypotheses are not being validated. "
                "Call `confirm(filename, observation)` or `contradict(filename, observation)` NOW "
                "for at least one of your hypotheses before taking another game action."
            )

        # Periodic evidence check reminder
        if self.step_count > 0 and self.step_count % 10 == 0:
            sections.append(
                "📝 EVIDENCE CHECK (MANDATORY):\n"
                "1. Do you have hypotheses with 0 confirmations? Pick ONE and `confirm(filename, observation)` or `contradict(filename, observation)` it NOW based on what you've seen.\n"
                "2. New raw fact? → `write_memory(folder='discoveries', ...)`\n"
                "3. New theory? → `write_memory(folder='hypotheses', ...)`\n"
                "⚠️ You MUST call confirm or contradict at least once before your next game action."
            )

        # POI awareness — highlight non-background, non-player objects the agent might want to investigate
        if latest.frame and self.step_count > 0 and self.step_count % 5 == 0:
            poi_info = self._detect_pois(latest.frame[0])
            if poi_info:
                sections.append(f"🔍 Points of Interest:\n{poi_info}")

        # Repetition detection — warn agent if it's looping the same actions
        if len(self.current_steps) >= 6:
            recent_actions = [s["action"] for s in self.current_steps[-10:]]
            # Detect 2-action cycle (e.g. UP DOWN UP DOWN)
            if len(recent_actions) >= 6:
                pair = recent_actions[-2:]
                cycle_count = 0
                for i in range(len(recent_actions) - 2, -1, -2):
                    if i >= 1 and recent_actions[i-1:i+1] == pair:
                        cycle_count += 1
                    else:
                        break
                if cycle_count >= 3:
                    sections.append(
                        f"🔴 REPETITION ALERT: You have repeated {pair[0]}→{pair[1]} {cycle_count} times! "
                        f"Score is still {score}. This is NOT working. STOP this loop immediately.\n"
                        "You MUST do something DIFFERENT:\n"
                        "- Move to a completely different area of the grid\n"
                        "- Try ACTION5 or ACTION6 (unexplored actions)\n"
                        "- Call `update_plan` with a fundamentally new strategy\n"
                        "Repeating the same actions expecting different results is wasting your limited steps."
                    )

        # Stuck detection → replan nudge
        steps_since_score = self.step_count - self._last_score_step
        if steps_since_score >= STUCK_THRESHOLD and (steps_since_score - STUCK_THRESHOLD) % HYPOTHESIS_INTERVAL == 0:
            logger.info("REPLAN NUDGE triggered at step %d (stuck for %d steps)", self.step_count, steps_since_score)
            sections.append(
                f"🔬 STUCK for {steps_since_score} steps without scoring. Your plan is NOT WORKING.\n"
                "1. Call `update_plan` with a FUNDAMENTALLY DIFFERENT approach\n"
                "2. What have you tried that failed? Don't repeat it.\n"
                "3. What part of the grid have you NOT explored?\n"
                "Your current plan is wrong. Change it before taking more actions."
            )

        # Predict-then-act with evidence loop (only show when not navigating)
        if not bfs_route_str:
            sections.append(
                "PREDICT → ACT → EVIDENCE loop:\n"
                "1. STATE PREDICTION: 'I expect [ACTION] will [effect] because [reason].'\n"
                "2. Call the ACTION.\n"
                "3. After observing: was your prediction correct?\n"
                "   - YES → `confirm(hypothesis_filename, 'Step N: [what happened, matching prediction]')`\n"
                "   - NO → `contradict(hypothesis_filename, 'Step N: expected X but got Y')`\n"
                "4. REMOTE EFFECTS: Did anything change AWAY from your player? If so:\n"
                "   - Check the 📐 PATTERN ANALYSIS — it auto-extracts the logical pattern\n"
                "   - Does it MATCH any target pattern? If yes, does the score change?\n"
                "   - If no match yet, press the button again to cycle — count how many states exist\n"
                "   - KEY INSIGHT: Pattern matching between areas can BE the scoring mechanism\n"
                "This is HOW you build verified knowledge. Raw actions without confirm/contradict waste steps."
            )

        # BFS route — LAST section for maximum recency effect
        if bfs_route_str:
            sections.append(bfs_route_str)

        return "\n".join(sections)

    def _detect_pois(self, grid: list[list[int]]) -> str:
        """Detect points of interest — non-background color clusters that may be interactive."""
        if not grid:
            return ""
        rows, cols = len(grid), len(grid[0])

        # Find background color
        color_count: Counter[int] = Counter()
        for r in range(4, rows - 4):
            for c in range(4, cols - 4):
                color_count[grid[r][c]] += 1
        if not color_count:
            return ""
        bg = color_count.most_common(1)[0][0]

        # Group non-bg colors with bounding boxes
        color_bounds: dict[int, list[int]] = {}  # color → [min_r, max_r, min_c, max_c, count]
        for r in range(4, rows - 4):
            for c in range(4, cols - 4):
                v = grid[r][c]
                if v != bg:
                    if v not in color_bounds:
                        color_bounds[v] = [r, r, c, c, 0]
                    b = color_bounds[v]
                    b[0] = min(b[0], r)
                    b[1] = max(b[1], r)
                    b[2] = min(b[2], c)
                    b[3] = max(b[3], c)
                    b[4] += 1

        if not color_bounds:
            return ""

        # Format: show each color cluster as a POI
        lines = []
        for color in sorted(color_bounds):
            b = color_bounds[color]
            min_r, max_r, min_c, max_c, count = b
            size = f"{max_r - min_r + 1}x{max_c - min_c + 1}"
            lines.append(f"- Color {color}: {count} cells, area ({min_r},{min_c})-({max_r},{max_c}) [{size}]")

        return "\n".join(lines[:15])  # Cap at 15 POIs

    def _force_score_review(self) -> None:
        """Force agent to record what caused a score increase. Called on level-up."""
        completed_level = self.current_level - 1

        # Build a richer summary with positions and world changes
        recent = self.current_steps[-20:] if self.current_steps else []
        action_lines = []
        for s in recent:
            line = f"Step {s['step']}: {s['action']} → {s['effect']}"
            if s.get('pos'):
                line += f" (pos={s['pos']})"
            action_lines.append(line)
        action_log = "\n".join(action_lines)

        # Find the scoring step and key world-change steps
        scoring_step = None
        world_change_steps = []
        for s in self.current_steps:
            if "scored" in s.get("effect", ""):
                scoring_step = s
            if s.get("world_changed"):
                world_change_steps.append(s)

        scoring_info = ""
        if scoring_step:
            scoring_info = (
                f"\n## Scoring step:\n"
                f"Step {scoring_step['step']}: {scoring_step['action']} at pos={scoring_step.get('pos','?')} → {scoring_step['effect']}\n"
            )
        world_info = ""
        if world_change_steps:
            wc_lines = [f"Step {s['step']}: {s['action']} at pos={s.get('pos','?')}" for s in world_change_steps[-5:]]
            world_info = f"\n## World-change triggers (last 5):\n" + "\n".join(wc_lines) + "\n"

        review_content = (
            f"---\n"
            f"name: \"Level {completed_level} win sequence\"\n"
            f"description: \"Actions that led to scoring on level {completed_level}\"\n"
            f"---\n\n"
            f"# How I scored on level {completed_level}\n\n"
            f"## Action sequence (last 20 steps before scoring):\n{action_log}\n"
            f"{scoring_info}{world_info}\n"
            f"## Key insight:\n"
            f"(AGENT MUST FILL THIS IN — see review prompt below)\n"
        )
        self.memory.write_file(
            "summaries",
            f"level{completed_level}-win.md",
            review_content,
            scope=f"level{completed_level}",
        )
        logger.info("Score review saved for level %d", completed_level)

        # Enable promote_to_shared for this review window
        self._in_score_review = True

        # Build a list of current level's knowledge for the agent to review
        level_knowledge = []
        for folder in ("verified", "hypotheses", "discoveries"):
            listing = self.memory.list_files(folder, scope=f"level{completed_level}")
            if "(empty" not in listing:
                level_knowledge.append(listing)
        knowledge_summary = "\n".join(level_knowledge) if level_knowledge else "(no files)"

        # Inject a structured review message forcing deep analysis
        self.messages.append({
            "role": "user",
            "content": (
                f"🎯 YOU SCORED! Level {completed_level} completed!\n\n"
                "⚠️ THIS IS THE MOST IMPORTANT MOMENT. You MUST complete ALL 3 steps below before taking any game action.\n\n"
                "═══════════════════════════════════════\n"
                "STEP 1 — CAUSAL ANALYSIS (write to summaries)\n"
                "═══════════════════════════════════════\n"
                f"Look at the action log in `level{completed_level}-win.md`. Answer these questions:\n"
                "1. **WHAT was the scoring action?** Which exact action at which position triggered the score?\n"
                "2. **WHY did it score?** What game mechanic was activated? (e.g., reached a goal, matched a pattern, cleared an obstacle)\n"
                "3. **WHAT was the setup?** What did you do BEFORE the scoring action to make it possible? "
                "(e.g., pressed a button N times to cycle a pattern, cleared a barrier, moved to a specific position)\n"
                "4. **HOW TO REPLICATE?** Write a step-by-step recipe: 'To score on a level like this: "
                "first do X, then Y, then Z.'\n\n"
                f"Call `write_memory(folder='summaries', filename='level{completed_level}-win.md', ...)` "
                "and FILL IN the 'Key insight' section with your answers. Be SPECIFIC — coordinates, colors, action counts.\n\n"
                "═══════════════════════════════════════\n"
                "STEP 2 — EXTRACT UNIVERSAL RULES (promote to shared)\n"
                "═══════════════════════════════════════\n"
                f"Your level {completed_level} knowledge:\n{knowledge_summary}\n\n"
                "For each file, ask: 'Would this help on a DIFFERENT level with a different layout?'\n"
                "- YES → `promote_to_shared(folder='...', filename='...', source_scope='level{cl}')`\n"
                "- NO (level-specific coordinates/paths) → skip\n\n"
                "Universal knowledge examples: action mappings, movement rules, scoring conditions, "
                "button/gate mechanics, pattern-cycling rules, object type behaviors.\n\n"
                "═══════════════════════════════════════\n"
                "STEP 3 — WRITE A SCORING RULE (update_skill)\n"
                "═══════════════════════════════════════\n"
                "Based on your analysis, call `update_skill` to add a concise scoring recipe that applies to future levels:\n"
                "Example: 'Scoring recipe: 1) Find button (c0/c1 cluster). 2) Step on/off button to cycle remote c9 pattern. "
                "3) When remote c9 matches target c9, navigate to goal (c9 cluster near border). 4) Step onto goal to score.'\n\n"
                "DO NOT skip any step. The knowledge you save here is the ONLY thing that persists to future levels."
            ).format(cl=completed_level),
        })

    def _force_failure_analysis(self, result: str) -> None:
        """LLM-based failure analysis after game_over/max_actions. Writes to summaries/."""
        if not self.current_steps:
            return

        # Build compact episode summary
        n = len(self.current_steps)
        max_score = max((s["score"] for s in self.current_steps), default=0)
        action_counts = Counter(s["action"] for s in self.current_steps)
        effect_counts = Counter(s["effect"] for s in self.current_steps)

        # Get memory snapshot for context
        memory_snapshot = self.memory.get_memory_snapshot()

        prompt = (
            f"Game episode ended: {result} after {n} steps. Max score: {max_score}.\n"
            f"Actions: {dict(action_counts.most_common())}\n"
            f"Effects: {dict(effect_counts.most_common())}\n\n"
            f"Last 20 steps:\n"
        )
        for s in self.current_steps[-20:]:
            prompt += f"  Step {s['step']}: {s['action']} → {s['effect']} (score={s['score']})\n"

        if memory_snapshot:
            prompt += f"\nCurrent memory:\n{memory_snapshot}\n"

        prompt += (
            "\nWrite a FAILURE ANALYSIS (under 200 words):\n"
            "1. What strategies were tried?\n"
            "2. What worked (even partially)?\n"
            "3. What clearly FAILED and should NOT be repeated?\n"
            "4. What should be tried DIFFERENTLY next episode?\n"
            "5. Which hypotheses should be kept vs disproved?\n"
            "Start with '---\\nname: ...' YAML frontmatter."
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            if response.usage:
                self.total_tokens += response.usage.total_tokens
            content = response.choices[0].message.content if response.choices else ""
            if content and len(content) > 50:
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.memory.write_file(
                    "summaries",
                    f"failure-analysis-ep{self.retry_count}-{ts}.md",
                    content,
                )
                logger.info("Failure analysis saved to summaries/")
        except Exception as e:
            logger.warning("Failure analysis generation failed: %s", e)

    # ── Message Log ────────────────────────────────────────────────────

    def _record_llm_call(self, request_msgs: list[dict[str, Any]], response: Any) -> None:
        """Append one LLM call (request + response) to the message JSONL log."""
        try:
            from datetime import datetime, timezone

            # Serialize full response via model_dump (pydantic) to capture ALL fields
            # including reasoning_content, thinking, etc.
            try:
                resp_data = response.model_dump()
            except Exception:
                # Fallback: manual serialization
                resp_data = {"_raw": str(response)}

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "llm_call": self.llm_calls,
                "step": self.step_count,
                "level": self.current_level,
                "episode": self.tree.episode,
                "model": self.model,
                "request": request_msgs,
                "response": resp_data,
            }

            self._msg_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._msg_log_path, "a", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.debug("Message log write failed: %s", e)

    # ── LLM API ───────────────────────────────────────────────────────

    def _call_llm(self) -> Optional[Any]:
        """Make LLM API call with retry."""
        system = self._build_system_prompt()
        msgs = [{"role": "system", "content": system}] + self._get_messages()

        for attempt in range(API_RETRIES):
            try:
                tc_mode = "auto" if "claude" in self.model else "required"
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    tools=self._build_tools(),
                    tool_choice=tc_mode,
                    extra_body={"include_reasoning": True},
                )
                if response.usage:
                    self.total_tokens += response.usage.total_tokens
                self.llm_calls += 1
                msg = response.choices[0].message if response.choices else None
                logger.info(
                    "LLM call %d: finish=%s, tool_calls=%d, content=%s",
                    self.llm_calls,
                    response.choices[0].finish_reason if response.choices else "?",
                    len(msg.tool_calls) if msg and msg.tool_calls else 0,
                    repr(msg.content[:80]) if msg and msg.content else "None",
                )
                # Record full LLM call to message log
                self._record_llm_call(msgs, response)
                return response
            except openai.AuthenticationError as e:
                logger.error("Auth error (non-retryable): %s", e)
                return None
            except openai.BadRequestError as e:
                error_msg = str(e)
                logger.error("LLM 400 error (attempt %d): %s", attempt + 1, e)
                if "Thought signature" in error_msg or "function response" in error_msg:
                    # Gemini-specific: message history is corrupt; trim aggressively
                    # but find a safe cut point (before a user message)
                    if len(self.messages) > 6:
                        cut = max(len(self.messages) - 6, 0)
                        while cut < len(self.messages) - 4:
                            if self.messages[cut].get("role") == "user":
                                break
                            cut += 1
                        self.messages = self.messages[cut:]
                        logger.info("Trimmed messages aggressively (kept %d) to fix Gemini error", len(self.messages))
                        msgs = [{"role": "system", "content": system}] + self._get_messages()
                        continue
                return None
            except (openai.APIConnectionError, openai.RateLimitError,
                    openai.APITimeoutError, TimeoutError) as e:
                logger.warning("LLM error (attempt %d): %s", attempt + 1, e)
                if attempt < API_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error("Unexpected LLM error: %s", e)
                if attempt < API_RETRIES - 1:
                    time.sleep(2)
                else:
                    return None
        return None

    def _get_messages(self) -> list[dict[str, Any]]:
        """Get conversation messages, trimmed to window.

        Ensures we never cut between assistant (tool_calls) and tool results.
        Also validates message ordering for Gemini compatibility.
        """
        if len(self.messages) <= MESSAGE_WINDOW:
            msgs = list(self.messages)
        else:
            # Find a safe start point: must be a user message (observation boundary)
            start = len(self.messages) - MESSAGE_WINDOW
            while start < len(self.messages) - 4:
                if self.messages[start].get("role") == "user":
                    break
                start += 1
            msgs = self.messages[start:]

        # Validate: every assistant with tool_calls must be immediately followed by tool responses
        validated: list[dict[str, Any]] = []
        i = 0
        while i < len(msgs):
            msg = msgs[i]
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Collect expected tool_call IDs
                tc_ids = {tc["id"] for tc in msg["tool_calls"]}
                # Check if following messages are the matching tool responses
                j = i + 1
                tool_responses = []
                while j < len(msgs) and msgs[j].get("role") == "tool":
                    tool_responses.append(msgs[j])
                    j += 1
                response_ids = {tr.get("tool_call_id") for tr in tool_responses}
                if tc_ids <= response_ids:
                    # Valid pair — include all
                    validated.append(msg)
                    validated.extend(tool_responses)
                    i = j
                else:
                    # Broken pair — skip this assistant and its orphan responses
                    logger.warning("Dropping broken assistant→tool pair (expected %s, got %s)", tc_ids, response_ids)
                    i = j
            else:
                validated.append(msg)
                i += 1

        return validated

    def _trim_messages(self) -> None:
        """Trim message history: summarize old messages, keep summary + recent window.

        Instead of discarding old messages, we compress them into a summary
        that becomes the first user message. This preserves context.
        """
        if len(self.messages) <= MESSAGE_WINDOW * 2:
            return

        target = len(self.messages) - MESSAGE_WINDOW
        cut = max(target, 0)

        # Walk forward to find a user message (start of a new turn)
        while cut < len(self.messages) - 4:
            if self.messages[cut].get("role") == "user":
                break
            cut += 1

        if cut >= len(self.messages) - 4:
            return  # Can't find safe cut, don't trim

        # Extract messages to be discarded
        old_messages = self.messages[:cut]
        recent_messages = self.messages[cut:]

        # Build text from old messages for summarization
        old_text = self._messages_to_text(old_messages)

        # Get existing summary if first message is already a summary
        existing_summary = ""
        if old_messages and old_messages[0].get("role") == "user":
            content = old_messages[0].get("content", "")
            if content.startswith("[HISTORY SUMMARY]"):
                existing_summary = content

        # Summarize via LLM (cheap, short prompt)
        summary = self._summarize_history(old_text, existing_summary)

        if summary:
            # Prepend summary as first user message
            self.messages = [{"role": "user", "content": summary}] + recent_messages
        else:
            # Fallback: just trim without summary
            self.messages = recent_messages

        logger.info("Trimmed messages: %d old → summary + %d recent = %d total",
                     len(old_messages), len(recent_messages), len(self.messages))

    def _messages_to_text(self, messages: list[dict[str, Any]]) -> str:
        """Convert messages to compact text for summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "?")
            if role == "user":
                content = msg.get("content", "")
                # Extract just the key info from observations
                for line in content.split("\n"):
                    if any(k in line for k in ["Step", "Score", "ACTION", "scored", "blocked", "moved", "History"]):
                        lines.append(line)
            elif role == "assistant":
                tcs = msg.get("tool_calls", [])
                for tc in tcs:
                    fn = tc.get("function", {})
                    name = fn.get("name", "?")
                    args = fn.get("arguments", "")
                    if name.startswith("ACTION"):
                        lines.append(f"Agent: {name}")
                    else:
                        # Truncate args for non-game tools
                        lines.append(f"Agent: {name}({args[:100]})")
            elif role == "tool":
                content = msg.get("content", "")
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"  → {content}")
        return "\n".join(lines[-80:])  # Cap at last 80 lines

    def _summarize_history(self, old_text: str, existing_summary: str) -> str:
        """Summarize old conversation history via a cheap LLM call."""
        if not old_text.strip():
            return existing_summary

        try:
            prompt = (
                "Compress the following game session history into a SHORT summary (under 300 words).\n"
                "Focus on:\n"
                "- What actions were tried and their effects (moved/blocked/scored)\n"
                "- Key discoveries made (what was learned about the game)\n"
                "- Hypotheses formed or disproved\n"
                "- Current position/situation\n"
                "- What approaches FAILED (so they are not repeated)\n\n"
                "Do NOT include grid data or coordinates unless critical.\n"
                "Start with '[HISTORY SUMMARY]'.\n"
            )
            if existing_summary:
                prompt += f"\nPrevious summary to merge with:\n{existing_summary}\n"
            prompt += f"\nNew history to summarize:\n{old_text}"

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            if response.usage:
                self.total_tokens += response.usage.total_tokens
            result = response.choices[0].message.content if response.choices else ""
            if result and not result.startswith("[HISTORY SUMMARY]"):
                result = "[HISTORY SUMMARY]\n" + result
            logger.info("History summary generated (%d chars)", len(result))
            return result
        except Exception as e:
            logger.warning("History summarization failed: %s", e)
            return existing_summary or ""

    # ── Tools Definition ──────────────────────────────────────────────

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build tool list for LLM."""
        tools = []

        # Game actions
        for i in range(1, 7):
            tools.append({
                "type": "function",
                "function": {
                    "name": f"ACTION{i}",
                    "description": f"Game action {i}. Meaning is unknown — discover through play.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            })

        # Memory tools
        scope_prop = {
            "type": "string",
            "description": (
                "Memory scope: 'current' (default=this level), 'shared' (game-wide, READ-ONLY — use promote_to_shared to add), "
                "or 'levelN' (e.g. 'level1') to access another level's memory."
            ),
        }

        tools.append({
            "type": "function",
            "function": {
                "name": "list_memory",
                "description": "List files in a memory folder. Returns filename, name, and description for each file. Use this BEFORE read_memory to find relevant files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "enum": ["hypotheses", "verified", "discoveries", "summaries", "disproved"],
                            "description": "Which memory folder to list",
                        },
                        "scope": scope_prop,
                    },
                    "required": ["folder"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "read_memory",
                "description": "Read full content of a specific memory file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder": {"type": "string", "enum": ["hypotheses", "verified", "discoveries", "summaries", "disproved"]},
                        "filename": {"type": "string", "description": "Filename (e.g., 'player-movement.md')"},
                        "scope": scope_prop,
                    },
                    "required": ["folder", "filename"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "write_memory",
                "description": (
                    "Write or update a memory file. Content MUST include YAML frontmatter:\n"
                    "---\nname: \"Short name\"\ndescription: \"One-line summary\"\n---\nDetailed content...\n\n"
                    "CRITICAL: ALWAYS UPDATE existing files instead of creating new ones with numbered suffixes. "
                    "If you have 'nav_strategy.md', do NOT create 'nav_strategy2.md' — overwrite 'nav_strategy.md' with updated content. "
                    "Use a SMALL number of well-maintained files, not many disposable ones.\n\n"
                    "FOLDER RULES:\n"
                    "- `discoveries`: ONLY raw factual observations (coordinates, colors, grid layouts, measured effects). "
                    "NO interpretations, NO guesses, NO game-type labels (e.g. 'Sokoban', 'Snake'). "
                    "Example: 'Color 12 block at (35,29) moved down 5 cells after ACTION2.'\n"
                    "- `hypotheses`: Your interpretations and theories about game mechanics. "
                    "Example: 'Moving onto color 1 cells may trigger scoring.'\n"
                    "- `verified`: CANNOT write directly — use `confirm` tool to add evidence; auto-promotes at 2✓.\n"
                    "- `disproved`: CANNOT write directly — use `contradict` tool; auto-disproves at 2✗.\n"
                    "- `summaries`: Strategy synthesis.\n\n"
                    "scope='shared' is READ-ONLY for writes — use `promote_to_shared` after scoring. "
                    "Use scope='current' (default) for level-specific data."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder": {"type": "string", "enum": ["hypotheses", "verified", "discoveries", "summaries", "disproved"]},
                        "filename": {"type": "string", "description": "Filename (e.g., 'player-movement.md')"},
                        "content": {"type": "string", "description": "Full file content with YAML frontmatter"},
                        "scope": scope_prop,
                    },
                    "required": ["folder", "filename", "content"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "confirm",
                "description": (
                    "Record a CONFIRMING observation for a hypothesis or discovery. "
                    "+1✓ count. Auto-promotes hypothesis → verified/ at 2✓. "
                    "CANNOT confirm already-verified rules. "
                    "Example: 'Step 15: ACTION1 at player (30,25) moved up 5 cells to (25,25). c9 wall at (20,25) nearby.'"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Hypothesis or discovery filename (NOT verified rules)"},
                        "observation": {
                            "type": "string",
                            "description": "MUST include: step number, action, player position (row,col), nearby objects, and result. 50+ chars.",
                        },
                        "scope": scope_prop,
                    },
                    "required": ["filename", "observation"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "contradict",
                "description": (
                    "Record a CONTRADICTING observation for a hypothesis or verified rule. "
                    "+1✗ count. Auto-disproves hypothesis at 2✗. Demotes verified rule when ✗ ≥ ✓. "
                    "IMPORTANT: 'blocked' does NOT always mean wrong — maybe there's a wall nearby! "
                    "Include your position and surroundings to distinguish 'wrong hypothesis' from 'blocked by obstacle'. "
                    "Example: 'Step 20: ACTION3 at player (40,29), blocked. c11 wall at (40,24) to left. Blocked by wall, not wrong mapping.'"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Hypothesis or verified rule filename"},
                        "observation": {
                            "type": "string",
                            "description": "MUST include: step number, player position (row,col), nearby objects/walls, and WHY this contradicts. 50+ chars.",
                        },
                        "scope": scope_prop,
                    },
                    "required": ["filename", "observation"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "update_plan",
                "description": (
                    "Update your STRATEGIC PLAN. This is your high-level plan that persists across steps. "
                    "Call this BEFORE taking game actions to set your strategy. "
                    "Call this AGAIN when your plan fails (blocked actions, wrong direction). "
                    "Your plan is shown in the system prompt every turn — keep it current. "
                    "Do NOT create nav_strategy files — use update_plan instead."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "description": "What are you trying to achieve? (e.g., 'Reach the button at (45,49) to open the gate')",
                        },
                        "route": {
                            "type": "string",
                            "description": "Step-by-step directions to get there (e.g., 'From (10,34): DOWN x6 to (40,34), then RIGHT x3 to (40,49)')",
                        },
                        "next_actions": {
                            "type": "string",
                            "description": "Your next 3-5 specific actions (e.g., 'ACTION2, ACTION2, ACTION2, ACTION4, ACTION4')",
                        },
                    },
                    "required": ["goal"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "update_skill",
                "description": (
                    "Add your own SUPPLEMENTARY notes about this level. "
                    "The base RULES are immutable and cannot be overridden. "
                    "Use this for: specific coordinates you discovered, paths that work, "
                    "timing observations, or corrections to your earlier wrong theories. "
                    "Do NOT contradict the base rules — if they say 'enclose goals', that IS how scoring works."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Full SKILL.md content — a comprehensive guide to playing this game",
                        },
                    },
                    "required": ["content"],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "promote_to_shared",
                "description": (
                    "Copy a memory file from a level scope to shared/ (game-wide). "
                    "ONLY available during score/level-up review. Use this to promote UNIVERSAL knowledge "
                    "that applies to ALL levels (action mappings, movement mechanics, object types, scoring rules). "
                    "Do NOT promote level-specific data (coordinates, layouts, specific paths)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "enum": ["hypotheses", "verified", "discoveries", "summaries", "disproved"],
                            "description": "Source folder",
                        },
                        "filename": {"type": "string", "description": "File to promote to shared/"},
                        "source_scope": {
                            "type": "string",
                            "description": "Source level scope (e.g., 'level1', 'current'). Defaults to current level.",
                        },
                    },
                    "required": ["folder", "filename"],
                },
            },
        })

        # Exploration tree tools
        tools.append({
            "type": "function",
            "function": {
                "name": "view_tree",
                "description": (
                    "Browse your exploration history tree. Each node records: state → action → result, "
                    "plus attached discoveries/hypotheses/proofs.\n"
                    "Modes:\n"
                    "- 'branch': show last N nodes on current path (default)\n"
                    "- 'world_changes': find nodes where the world changed remotely\n"
                    "- 'scores': find all scoring events\n"
                    "- 'search': search nodes by keyword (action, effect, artifact name)\n"
                    "- 'stats': quick tree statistics"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["branch", "world_changes", "scores", "search", "stats"],
                            "description": "What to view",
                        },
                        "count": {
                            "type": "integer",
                            "description": "How many nodes to show (default 20)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for mode='search')",
                        },
                    },
                    "required": [],
                },
            },
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "view_node",
                "description": (
                    "View full details of a specific exploration node by ID (e.g. 'ep0.s15'). "
                    "Shows state, action, result, and all attached artifact filenames. "
                    "Use read_memory to open any artifact file listed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "Node ID (e.g. 'ep0.s15'). Find IDs via view_tree.",
                        },
                    },
                    "required": ["node_id"],
                },
            },
        })

        return tools

    # ── Video Generation ─────────────────────────────────────────────

    def _generate_live_video(self) -> None:
        """Generate a live video from the current recording."""
        if not hasattr(self, "recorder") or not self.recorder.filename:
            return
        try:
            import importlib.util
            viz_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "scripts", "visualize_recording.py",
            )
            if not os.path.exists(viz_path):
                return
            spec = importlib.util.spec_from_file_location("visualize_recording", viz_path)
            viz = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(viz)

            rec_path = self.recorder.filename
            events = viz.load_events(rec_path)
            if not events:
                return

            mp4_path = rec_path.rsplit(".", 1)[0] + "_live.mp4"
            viz.build_mp4(events, mp4_path, fps=5)
            logger.info("Live video updated: %s (%d frames)", mp4_path, len(events))
        except Exception as e:
            logger.debug("Live video generation failed: %s", e)

    # ── Postmortem & State ────────────────────────────────────────────

    def _save_postmortem(self, result: str) -> None:
        """Save episode summary after failure."""
        if not self.current_steps:
            return

        n = len(self.current_steps)
        max_score = max((s["score"] for s in self.current_steps), default=0)
        action_counts = Counter(s["action"] for s in self.current_steps)
        effect_counts = Counter(s["effect"] for s in self.current_steps)

        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ep{self.retry_count}-{result}-{ts}.md"

        content = (
            f"---\n"
            f"name: \"Episode {self.retry_count} — {result}\"\n"
            f"description: \"{n} steps, max_score={max_score}, {result}\"\n"
            f"---\n\n"
            f"# Episode {self.retry_count} Postmortem\n"
            f"- Result: {result}\n"
            f"- Steps: {n}\n"
            f"- Max score: {max_score}\n"
            f"- Actions: {dict(action_counts.most_common())}\n"
            f"- Effects: {dict(effect_counts.most_common())}\n\n"
            f"## Action Log (last 20)\n"
        )
        for s in self.current_steps[-20:]:
            content += f"- Step {s['step']}: {s['action']} → {s['effect']} (score={s['score']})\n"

        self.memory.write_file("discoveries", filename, content)
        logger.info("Postmortem saved: discoveries/%s", filename)

    def _update_game_facts(self) -> None:
        """Extract universal game mechanics from current level's skill into game-wide FACTS.md."""
        # Gather all level skill files + verified memories
        skill_base = self._skill_base_dir / self.game_id
        sources = []

        # Current level's SKILL.md
        skill_path = skill_base / f"level{self.current_level}" / "SKILL.md"
        if skill_path.is_file():
            content = skill_path.read_text(encoding="utf-8").strip()
            if len(content) > 50:
                sources.append(f"# Level {self.current_level} Skill:\n{content}")

        # All verified memories (shared + current level)
        for scope in ["shared", f"level{self.current_level}"]:
            verified = self.memory.list_files_parsed("verified", scope=scope)
            for v in verified:
                vcontent = self.memory.read_file("verified", v["filename"], scope=scope)
                sources.append(f"# Verified ({scope}): {v['name']}\n{vcontent}")

        if not sources:
            return

        # Load existing FACTS.md
        facts_path = skill_base / "FACTS.md"
        existing_facts = ""
        if facts_path.is_file():
            existing_facts = facts_path.read_text(encoding="utf-8").strip()

        # LLM call to extract/merge universal facts
        extract_msgs = [
            {"role": "system", "content": (
                "You are extracting UNIVERSAL GAME MECHANICS from level-specific knowledge.\n\n"
                "Output a concise FACTS.md containing ONLY things true for ALL levels:\n"
                "- Movement mechanics (player shape, step size, controls)\n"
                "- Object types and their effects (buttons, gates, collectibles, timers)\n"
                "- Interaction rules (how to activate objects, scoring triggers)\n"
                "- Resource management (timer mechanics, time extensions)\n"
                "- Action mappings (what each ACTION does)\n\n"
                "Rules:\n"
                "- NO coordinates or level-specific layouts\n"
                "- NO strategy or pathing advice\n"
                "- MERGE with existing facts — never lose confirmed facts\n"
                "- Be SPECIFIC: use color numbers, exact sizes, precise mechanics\n"
                "- Keep under 600 words — this is a quick-reference card\n"
                "- Output ONLY the FACTS.md content, no preamble"
            )},
            {"role": "user", "content": (
                (f"# Existing Game Facts:\n```\n{existing_facts}\n```\n\n" if existing_facts else "")
                + "\n\n".join(sources[:3])  # Limit to avoid huge prompts
                + "\n\nExtract and merge universal game mechanics into FACTS.md."
            )},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=extract_msgs,
                max_tokens=1000,
            )
            if response.choices and response.choices[0].message.content:
                facts_content = response.choices[0].message.content.strip()
                if len(facts_content) > 50:
                    skill_base.mkdir(parents=True, exist_ok=True)
                    facts_path.write_text(facts_content, encoding="utf-8")
                    logger.info("FACTS.md updated for %s (%d chars)", self.game_id, len(facts_content))
        except Exception as e:
            logger.warning("Failed to update game facts: %s", e)

    def _reset_state(self) -> None:
        """Reset state for next attempt."""
        self.tree.save()  # persist tree before reset
        self.tree.new_episode()  # branch the tree
        self.messages.clear()
        self.current_steps.clear()
        self.frames.clear()
        self.step_count = 0
        self._last_score_step = 0
        self._last_meta_summary_step = 0
        self._in_score_review = False
        self._last_evidence_step = 0

    def _log_stats(self) -> None:
        """Log final stats."""
        self.tree.save()  # persist tree at end
        logger.info(
            "Final stats: %d LLM calls, %d total tokens, %d game actions",
            self.llm_calls, self.total_tokens, self.step_count,
        )
        if self.llm_calls:
            logger.info(
                "Efficiency: %.1f calls/action, %d avg tokens/call",
                self.llm_calls / max(self.step_count, 1),
                self.total_tokens // self.llm_calls,
            )
