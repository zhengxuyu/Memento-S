"""
Game Intelligence Modules for ReactBufferAgent.

Three algorithmic assistants that give the LLM structured intelligence
without consuming any extra LLM tokens:

1. **GridNavigator** -- BFS pathfinding + spatial memory.  The LLM calls
   ``navigate_to(row, col)`` and gets an optimal action sequence back.
2. **InteractionTracker** -- Detects cause-and-effect relationships
   (collected object -> energy refill) purely from grid diffs.
3. **ObjectInventory** -- Tracks all interactive objects and suggests the
   next target based on priority (energy refills > prerequisites > goal).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# Step size for player movement (cells per action)
STEP_SIZE = 5


# =============================================================================
# Module A: GridNavigator -- Pathfinding + Spatial Memory
# =============================================================================


class SpatialMemory:
    """Tracks walls and walkable cells at step-size resolution."""

    def __init__(self) -> None:
        # (r, c) -> set of directions blocked from that position
        self._walls: dict[tuple[int, int], set[str]] = {}
        # Confirmed walkable positions
        self._walkable: set[tuple[int, int]] = set()
        # Inferred floor color (from grid analysis bg_color)
        self._floor_color: int = -1
        # Inferred unwalkable positions from static grid analysis
        self._unwalkable: set[tuple[int, int]] = set()
        # Visit counter: (r, c) -> number of times the player has been here
        self._visit_counts: dict[tuple[int, int], int] = {}

    def record_wall(self, pos: tuple[int, int], direction: str) -> None:
        """Record that moving in *direction* from *pos* is blocked."""
        if pos not in self._walls:
            self._walls[pos] = set()
        self._walls[pos].add(direction)

    def record_walkable(self, pos: tuple[int, int]) -> None:
        """Record that *pos* is a confirmed walkable position."""
        self._walkable.add(pos)
        # Remove from unwalkable if it was inferred
        self._unwalkable.discard(pos)

    def record_visit(self, pos: tuple[int, int]) -> None:
        """Increment visit count for a quantized position."""
        self._visit_counts[pos] = self._visit_counts.get(pos, 0) + 1

    def is_blocked(self, pos: tuple[int, int], direction: str) -> bool:
        """Return True if *direction* from *pos* is a known wall."""
        return direction in self._walls.get(pos, set())

    def is_unwalkable(self, pos: tuple[int, int]) -> bool:
        """Return True if *pos* was inferred as unwalkable from grid analysis."""
        return pos in self._unwalkable and pos not in self._walkable

    def infer_walkability_from_grid(
        self,
        grid: list[list[int]],
        bg_color: int,
        grid_h: int,
        grid_w: int,
    ) -> None:
        """Infer unwalkable cells from static grid analysis.

        Simple heuristic: for each STEP_SIZE x STEP_SIZE block, if >50%
        of cells are non-background color, mark as unwalkable.  Large
        same-color regions are almost always walls/structures in grid
        games; small interactive objects won't dominate a full block.

        Confirmed walkable positions always override static inference.
        """
        self._floor_color = bg_color
        self._unwalkable.clear()

        if not grid or grid_h == 0 or grid_w == 0:
            return

        step = STEP_SIZE
        unwalkable_count = 0
        for qr in range(0, grid_h, step):
            for qc in range(0, grid_w, step):
                # Already confirmed walkable — skip
                if (qr, qc) in self._walkable:
                    continue

                # Count non-background cells in this block
                non_bg = 0
                total_cells = 0
                for dr in range(step):
                    for dc in range(step):
                        r, c = qr + dr, qc + dc
                        if r < grid_h and c < grid_w:
                            total_cells += 1
                            if grid[r][c] != bg_color:
                                non_bg += 1

                # If >50% non-background, mark as unwalkable
                if total_cells > 0 and non_bg > total_cells * 0.5:
                    self._unwalkable.add((qr, qc))
                    unwalkable_count += 1

        logger.info(
            "Static wall detection: %d unwalkable blocks (bg_color=%d)",
            unwalkable_count, bg_color,
        )

    def invalidate_near(self, pos: tuple[int, int], radius: int = 3) -> int:
        """Invalidate confirmed walls within *radius* steps of *pos*.

        Called when a trigger/collectible changes the grid layout —
        nearby walls may no longer exist.

        Returns the number of wall edges removed.
        """
        removed = 0
        pr, pc = pos
        to_remove: list[tuple[int, int]] = []
        for wall_pos, dirs in self._walls.items():
            dist = abs(wall_pos[0] - pr) + abs(wall_pos[1] - pc)
            if dist <= radius * STEP_SIZE:
                removed += len(dirs)
                to_remove.append(wall_pos)
        for wp in to_remove:
            del self._walls[wp]
        # Also remove from unwalkable
        to_discard: list[tuple[int, int]] = []
        for uwp in self._unwalkable:
            dist = abs(uwp[0] - pr) + abs(uwp[1] - pc)
            if dist <= radius * STEP_SIZE:
                to_discard.append(uwp)
        for uwp in to_discard:
            self._unwalkable.discard(uwp)
        return removed

    def soft_reset(self) -> None:
        """Reset per-episode state but keep walls (they persist across retries)."""
        self._walkable.clear()
        self._unwalkable.clear()
        # _walls are kept — same game = same walls
        # _floor_color is kept

    def reset(self) -> None:
        """Full reset (clears everything including walls)."""
        self._walls.clear()
        self._walkable.clear()
        self._unwalkable.clear()
        self._floor_color = -1

    def stats(self) -> dict[str, int]:
        """Return summary stats."""
        return {
            "walls": sum(len(v) for v in self._walls.values()),
            "walkable": len(self._walkable),
            "unwalkable": len(self._unwalkable),
        }


# Direction constants
_DIR_DELTAS: dict[str, tuple[int, int]] = {
    "UP": (-STEP_SIZE, 0),
    "DOWN": (STEP_SIZE, 0),
    "LEFT": (0, -STEP_SIZE),
    "RIGHT": (0, STEP_SIZE),
}

_OPPOSITE_DIR: dict[str, str] = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
}


class GridNavigator:
    """BFS pathfinding on the step-quantized grid.

    The LLM calls ``navigate_to(target_r, target_c)`` and gets back an
    action sequence that avoids known walls.
    """

    # Default action→direction mappings (most common in ARC-AGI-3 games).
    # Actual observations from perception override these.
    _DEFAULT_MAPPINGS: dict[str, str] = {
        "UP": "ACTION1",
        "DOWN": "ACTION2",
        "LEFT": "ACTION3",
        "RIGHT": "ACTION4",
    }

    def __init__(self) -> None:
        self.memory = SpatialMemory()
        # direction -> action name (learned from perception._action_effects)
        # Pre-seed with common defaults so BFS works before all actions are tried.
        self._dir_to_action: dict[str, str] = dict(self._DEFAULT_MAPPINGS)
        # action -> direction (reverse mapping)
        self._action_to_dir: dict[str, str] = {
            v: k for k, v in self._DEFAULT_MAPPINGS.items()
        }
        # Grid dimensions (set on first infer call)
        self._grid_h: int = 64
        self._grid_w: int = 64
        self._initialized: bool = False

    def update_action_mappings(
        self, action_effects: dict[str, list[tuple[int, int]]]
    ) -> None:
        """Consume perception._action_effects to build direction<->action mapping."""
        for action_name, effects in action_effects.items():
            if not effects:
                continue
            # Never use RESET or non-movement actions for navigation
            if action_name in ("RESET", "ACTION5", "ACTION6"):
                continue
            # Use the most common direction
            dir_counts: dict[str, int] = {}
            for dr, dc in effects:
                if dr == 0 and dc == 0:
                    continue
                if dr < 0 and dc == 0:
                    d = "UP"
                elif dr > 0 and dc == 0:
                    d = "DOWN"
                elif dr == 0 and dc < 0:
                    d = "LEFT"
                elif dr == 0 and dc > 0:
                    d = "RIGHT"
                else:
                    continue  # diagonal, skip
                dir_counts[d] = dir_counts.get(d, 0) + 1

            if dir_counts:
                best_dir = max(dir_counts, key=dir_counts.get)
                self._dir_to_action[best_dir] = action_name
                self._action_to_dir[action_name] = best_dir

    def update_from_action_result(
        self,
        player_pos: tuple[int, int],
        action: str,
        moved: bool,
        new_player_pos: Optional[tuple[int, int]],
    ) -> None:
        """Record wall if no movement, walkable if moved.

        Args:
            player_pos: Player position before action (row, col).
            action: Action name (e.g. "ACTION1").
            moved: Whether the action resulted in movement.
            new_player_pos: Player position after action, if moved.
        """
        # Skip non-navigation actions
        if action in ("RESET", "ACTION5", "ACTION6"):
            return
        direction = self._action_to_dir.get(action)
        if direction is None:
            return

        # Quantize to step boundaries
        qr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
        qc = (player_pos[1] // STEP_SIZE) * STEP_SIZE

        if not moved:
            self.memory.record_wall((qr, qc), direction)
            # Also record the reverse: if UP from (r,c) is blocked,
            # then DOWN from (r-STEP, c) is also blocked (same wall edge).
            dr, dc = _DIR_DELTAS[direction]
            neighbor = (qr + dr, qc + dc)
            if 0 <= neighbor[0] < self._grid_h and 0 <= neighbor[1] < self._grid_w:
                self.memory.record_wall(neighbor, _OPPOSITE_DIR[direction])
        elif new_player_pos is not None:
            nqr = (new_player_pos[0] // STEP_SIZE) * STEP_SIZE
            nqc = (new_player_pos[1] // STEP_SIZE) * STEP_SIZE
            self.memory.record_walkable((nqr, nqc))
            self.memory.record_walkable((qr, qc))

    def infer_floor_and_walls(
        self,
        grid: list[list[int]],
        bg_color: int,
    ) -> None:
        """One-time static grid analysis for floor vs wall inference."""
        self._grid_h = len(grid)
        self._grid_w = len(grid[0]) if self._grid_h > 0 else 0
        self.memory.infer_walkability_from_grid(
            grid, bg_color, self._grid_h, self._grid_w
        )
        self._initialized = True

    def refresh_walkability(
        self,
        grid: list[list[int]],
        bg_color: int,
    ) -> None:
        """Re-run walkability inference on the current grid.

        Called after trigger collection or other grid-changing events
        to update the stale unwalkable set.  Confirmed walkable
        positions are preserved.
        """
        self._grid_h = len(grid)
        self._grid_w = len(grid[0]) if self._grid_h > 0 else 0
        self.memory.infer_walkability_from_grid(
            grid, bg_color, self._grid_h, self._grid_w
        )
        logger.info(
            "Navigator: refreshed walkability (unwalkable=%d, walkable=%d)",
            len(self.memory._unwalkable),
            len(self.memory._walkable),
        )

    def navigate_to(
        self,
        target_r: int,
        target_c: int,
        player_r: int,
        player_c: int,
        max_steps: int = 30,
        log: bool = True,
    ) -> Optional[list[str]]:
        """BFS pathfinding from player to target, returns action sequence.

        Uses a two-pass strategy:
        1. Conservative: block confirmed walls + inferred unwalkable cells.
        2. Optimistic fallback: block only confirmed walls.

        Returns:
            List of action names, or None if no path found.
        """
        if not self._dir_to_action:
            logger.info("navigate_to: no direction mappings yet")
            return None

        start = (
            (player_r // STEP_SIZE) * STEP_SIZE,
            (player_c // STEP_SIZE) * STEP_SIZE,
        )
        goal = (
            (target_r // STEP_SIZE) * STEP_SIZE,
            (target_c // STEP_SIZE) * STEP_SIZE,
        )
        if log:
            logger.info(
                "navigate_to: start=%s goal=%s dirs=%s walls=%d unwalkable=%d",
                start, goal, dict(self._dir_to_action),
                sum(len(v) for v in self.memory._walls.values()),
                len(self.memory._unwalkable),
            )

        if start == goal:
            return []

        # Pass 1: conservative (use inferred unwalkable)
        result = self._bfs(start, goal, max_steps, use_inferred=True)
        if result is not None:
            return result

        # Pass 2: optimistic (ignore inferred, only confirmed walls)
        return self._bfs(start, goal, max_steps, use_inferred=False)

    def _bfs(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        max_steps: int,
        use_inferred: bool,
    ) -> Optional[list[str]]:
        """Core BFS. If use_inferred, also block inferred-unwalkable nodes."""
        queue: deque[tuple[tuple[int, int], list[str]]] = deque()
        queue.append((start, []))
        visited: set[tuple[int, int]] = {start}

        while queue:
            pos, path = queue.popleft()

            if len(path) >= max_steps:
                continue

            for direction, (dr, dc) in _DIR_DELTAS.items():
                nr, nc = pos[0] + dr, pos[1] + dc

                if nr < 0 or nr >= self._grid_h or nc < 0 or nc >= self._grid_w:
                    continue

                if (nr, nc) in visited:
                    continue

                # Skip confirmed walls
                if self.memory.is_blocked(pos, direction):
                    continue

                # Skip inferred unwalkable (conservative pass only)
                if use_inferred and self.memory.is_unwalkable((nr, nc)):
                    continue

                action = self._dir_to_action.get(direction)
                if action is None:
                    continue

                new_path = path + [action]

                if (nr, nc) == goal:
                    return new_path

                visited.add((nr, nc))
                queue.append(((nr, nc), new_path))

        return None

    def compute_suggested_path(
        self,
        player_pos: tuple[int, int],
        target_pos: tuple[int, int],
        max_steps: int = 30,
    ) -> Optional[list[str]]:
        """Compute BFS path avoiding confirmed wall edges only.

        Returns list of action names, or None if no path found.
        """
        if not self._dir_to_action:
            return None
        start = (
            (player_pos[0] // STEP_SIZE) * STEP_SIZE,
            (player_pos[1] // STEP_SIZE) * STEP_SIZE,
        )
        goal = (
            (target_pos[0] // STEP_SIZE) * STEP_SIZE,
            (target_pos[1] // STEP_SIZE) * STEP_SIZE,
        )
        if start == goal:
            return None
        # Use confirmed wall edges only (no static inference)
        path = self._bfs(start, goal, max_steps=max_steps, use_inferred=False)
        if path is None or len(path) == 0:
            return None
        return path

    def get_status_summary(
        self,
        player_pos: Optional[tuple[int, int]] = None,
        targets: Optional[list[tuple[int, int, str]]] = None,
    ) -> str:
        """Text for prompt injection.

        Args:
            player_pos: Current player (row, col).
            targets: List of (row, col, description) for inventory targets,
                     ordered by priority (first = suggested next).
        """
        stats = self.memory.stats()
        if not self._initialized and stats["walls"] == 0:
            return ""

        parts: list[str] = ["# NAVIGATOR STATUS"]
        parts.append(
            f"Spatial memory: {stats['walkable']} walkable, "
            f"{stats['walls']} wall edges, "
            f"{stats['unwalkable']} inferred unwalkable"
        )

        if self._dir_to_action:
            mappings = ", ".join(
                f"{d}={a}" for d, a in sorted(self._dir_to_action.items())
            )
            parts.append(f"Direction mappings: {mappings}")
        else:
            parts.append("Direction mappings: not yet learned")

        # BFS suggested paths disabled — LLM navigates on its own.

        return "\n".join(parts)

    def get_exploration_suggestions(
        self,
        player_pos: Optional[tuple[int, int]] = None,
        n: int = 3,
    ) -> list[tuple[int, int]]:
        """Return unvisited positions adjacent to visited ones, sorted by distance.

        This is the "exploration frontier" — positions the agent hasn't been to
        but could reach from places it's already been. Helps avoid repeatedly
        visiting the same area.
        """
        visited = set(self.memory._visit_counts.keys())
        if not visited or player_pos is None:
            return []

        frontier: set[tuple[int, int]] = set()
        for vr, vc in visited:
            for dr, dc in _DIR_DELTAS.values():
                nr, nc = vr + dr, vc + dc
                if (
                    0 <= nr < self._grid_h
                    and 0 <= nc < self._grid_w
                    and (nr, nc) not in visited
                    and not self.memory.is_unwalkable((nr, nc))
                ):
                    frontier.add((nr, nc))

        if not frontier:
            return []

        pr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
        pc = (player_pos[1] // STEP_SIZE) * STEP_SIZE
        # Sort by distance from player, return top n
        by_dist = sorted(
            frontier,
            key=lambda p: abs(p[0] - pr) + abs(p[1] - pc),
        )
        return by_dist[:n]

    def flood_fill_reachable(
        self,
        start_r: int,
        start_c: int,
    ) -> set[tuple[int, int]]:
        """Flood-fill from player position on quantized grid.

        Returns set of (qr, qc) positions reachable from start,
        respecting both confirmed walls and inferred unwalkable cells.
        """
        start = (
            (start_r // STEP_SIZE) * STEP_SIZE,
            (start_c // STEP_SIZE) * STEP_SIZE,
        )
        visited: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            pos = queue.popleft()
            for direction, (dr, dc) in _DIR_DELTAS.items():
                nr, nc = pos[0] + dr, pos[1] + dc

                if nr < 0 or nr >= self._grid_h or nc < 0 or nc >= self._grid_w:
                    continue
                if (nr, nc) in visited:
                    continue
                # Skip confirmed walls
                if self.memory.is_blocked(pos, direction):
                    continue
                # Skip inferred unwalkable
                if self.memory.is_unwalkable((nr, nc)):
                    continue

                visited.add((nr, nc))
                queue.append((nr, nc))

        logger.info(
            "Flood-fill from (%d,%d): %d reachable cells",
            start_r, start_c, len(visited),
        )
        return visited

    def soft_reset(self) -> None:
        """Reset for retry — keep walls and action mappings."""
        self.memory.soft_reset()
        # Keep _initialized and _dir_to_action/_action_to_dir — same game mechanics

    def reset(self) -> None:
        """Full reset (clears everything)."""
        self.memory.reset()
        self._initialized = False


# =============================================================================
# Module B: InteractionTracker -- Cause-and-Effect Detection
# =============================================================================


class InteractionEventType(Enum):
    COLLECTED = "COLLECTED"
    APPEARED = "APPEARED"
    ENERGY = "ENERGY"
    SCORED = "SCORED"
    TOGGLED = "TOGGLED"  # same position collected then re-appeared (or vice versa)


@dataclass
class InteractionEvent:
    """A single detected interaction event."""

    step: int
    event_type: InteractionEventType
    description: str
    object_color: Optional[int] = None
    position: Optional[tuple[int, int]] = None
    energy_delta: int = 0
    score_delta: int = 0


@dataclass
class InteractionRule:
    """A learned cause-and-effect rule."""

    trigger_color: int
    effect: str  # "energy_refill", "score_increase", "appears", etc.
    confidence: int = 0  # number of observations
    avg_energy_delta: float = 0.0
    avg_score_delta: float = 0.0

    def describe(self) -> str:
        parts = [f"Color {self.trigger_color}"]
        if self.effect == "energy_refill":
            parts.append(
                f"-> energy refill (+{self.avg_energy_delta:.0f})"
            )
        elif self.effect == "score_increase":
            parts.append(
                f"-> score increase (+{self.avg_score_delta:.0f})"
            )
        else:
            parts.append(f"-> {self.effect}")
        parts.append(f"[{self.confidence} observations]")
        return " ".join(parts)


@dataclass
class TriggerHypothesis:
    """A hypothesized cause-effect link between a special object and a transformation."""

    step: int
    trigger_pos: tuple[int, int]  # (row, col) of the trigger object
    trigger_shape: str  # e.g. "cross", "diamond", "T-shape", "L-shape"
    trigger_color: int
    effect_type: str  # TransformationType value, e.g. "ROTATION_90"
    effect_region: Optional[tuple[int, int, int, int]]  # (r1, c1, r2, c2)
    effect_description: str
    confidence: int = 1  # 1 = hypothesis, >=2 = confirmed pattern


class InteractionTracker:
    """Algorithmically detects what happened after each action and learns rules.

    Zero LLM cost -- works purely from grid diffs and score/energy comparisons.
    """

    # Positions within this Manhattan distance are considered "same location"
    _TOGGLE_RADIUS: int = 8
    # Special shapes that are likely triggers
    _TRIGGER_SHAPES: frozenset[str] = frozenset(
        {"cross", "diamond", "T-shape", "L-shape", "U-shape"}
    )

    def __init__(self) -> None:
        self._events: list[InteractionEvent] = []
        # trigger_color -> InteractionRule
        self._rules: dict[int, InteractionRule] = {}
        # Track energy bar length for delta detection
        self._last_energy_length: Optional[int] = None
        # Energy bar row (auto-detected)
        self._energy_row: Optional[int] = None
        self._energy_color: int = 11  # default: dark green

        # Toggle detection: tracks positions where objects were collected/appeared
        # Key: (color, quantized_row, quantized_col), Value: list of (step, "collected"|"appeared")
        self._toggle_history: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
        # Confirmed toggle positions (persists across retries)
        self._toggle_positions: set[tuple[int, int, int]] = set()  # (color, qr, qc)

        # Trigger hypothesis tracking
        self._trigger_hypotheses: list[TriggerHypothesis] = []  # recent hypotheses
        # Confirmed patterns: key = (shape, color, effect_type) -> best hypothesis
        self._trigger_patterns: dict[tuple[str, int, str], TriggerHypothesis] = {}
        # Trigger activation counts: quantized (qr, qc) -> (count, last_score)
        # Used to soft-block navigate_to after too many fruitless activations
        self._trigger_activations: dict[tuple[int, int], tuple[int, int]] = {}
        # Trigger effect log: quantized (qr, qc) -> list of (step, effect_desc)
        self._trigger_effect_log: dict[tuple[int, int], list[tuple[int, str]]] = {}

    def track_step(
        self,
        step_num: int,
        prev_grid: Optional[list[list[int]]],
        curr_grid: Optional[list[list[int]]],
        player_pos: Optional[tuple[int, int]],
        score_before: int,
        score_after: int,
        action: str,
    ) -> list[InteractionEvent]:
        """Detect interactions from grid changes.

        Returns list of events detected this step.
        """
        events: list[InteractionEvent] = []

        if prev_grid is None or curr_grid is None:
            return events

        # Detect energy bar
        curr_energy = self._detect_energy_bar(curr_grid)
        prev_energy = self._detect_energy_bar(prev_grid)
        energy_delta = 0
        if curr_energy is not None and prev_energy is not None:
            energy_delta = curr_energy - prev_energy
            self._last_energy_length = curr_energy

        # Score change
        score_delta = score_after - score_before
        if score_delta > 0:
            events.append(InteractionEvent(
                step=step_num,
                event_type=InteractionEventType.SCORED,
                description=f"Score increased by {score_delta}",
                score_delta=score_delta,
            ))

        # Find disappeared objects near player
        disappeared = self._find_disappeared_near_player(
            prev_grid, curr_grid, player_pos
        )

        for color, pos in disappeared:
            events.append(InteractionEvent(
                step=step_num,
                event_type=InteractionEventType.COLLECTED,
                description=f"Color {color} object at ({pos[0]},{pos[1]}) disappeared (collected)",
                object_color=color,
                position=pos,
                energy_delta=energy_delta,
                score_delta=score_delta,
            ))

            # Correlate: COLLECTED + energy change -> update rule
            if energy_delta != 0:
                self._update_rule(color, "energy_refill", energy_delta, 0)
            if score_delta > 0:
                self._update_rule(color, "score_increase", 0, score_delta)

        # Energy event (even without collection)
        if energy_delta != 0 and not disappeared:
            events.append(InteractionEvent(
                step=step_num,
                event_type=InteractionEventType.ENERGY,
                description=f"Energy changed by {energy_delta}",
                energy_delta=energy_delta,
            ))

        # Find newly appeared objects
        appeared = self._find_appeared(prev_grid, curr_grid, player_pos)
        for color, pos in appeared:
            events.append(InteractionEvent(
                step=step_num,
                event_type=InteractionEventType.APPEARED,
                description=f"Color {color} object appeared at ({pos[0]},{pos[1]})",
                object_color=color,
                position=pos,
            ))

        # --- Toggle detection ---
        # Record disappearances and appearances in toggle history,
        # then check if a position flipped (collected → appeared or vice versa).
        for color, pos in disappeared:
            qr = (pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (pos[1] // STEP_SIZE) * STEP_SIZE
            key = (color, qr, qc)
            self._toggle_history.setdefault(key, []).append(
                (step_num, "collected")
            )
            self._check_toggle(key, step_num, events)

        for color, pos in appeared:
            qr = (pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (pos[1] // STEP_SIZE) * STEP_SIZE
            key = (color, qr, qc)
            self._toggle_history.setdefault(key, []).append(
                (step_num, "appeared")
            )
            self._check_toggle(key, step_num, events)

        self._events.extend(events)
        return events

    def _check_toggle(
        self,
        key: tuple[int, int, int],
        step_num: int,
        events: list[InteractionEvent],
    ) -> None:
        """Check if a position has toggled (collected then appeared, or vice versa)."""
        history = self._toggle_history.get(key, [])
        if len(history) < 2:
            return

        # Look for alternating pattern: last two entries have different types
        prev_type = history[-2][1]
        curr_type = history[-1][1]
        if prev_type != curr_type:
            color, qr, qc = key
            self._toggle_positions.add(key)
            events.append(InteractionEvent(
                step=step_num,
                event_type=InteractionEventType.TOGGLED,
                description=(
                    f"TOGGLE detected: color {color} at ({qr},{qc}) "
                    f"was {prev_type} then {curr_type} — "
                    f"DO NOT revisit this position"
                ),
                object_color=color,
                position=(qr, qc),
            ))
            logger.warning(
                "Toggle detected: color %d at (%d,%d), history=%s",
                color, qr, qc,
                [(s, t) for s, t in history[-4:]],
            )

    def get_toggle_warnings(self) -> str:
        """Format toggle warnings for prompt injection."""
        if not self._toggle_positions:
            return ""
        lines: list[str] = [
            "# TOGGLE WARNING — DO NOT REVISIT THESE POSITIONS",
            "These positions toggle ON/OFF when you step on them. "
            "If you already activated one, moving back over it will UNDO it!",
        ]
        for color, qr, qc in sorted(self._toggle_positions):
            lines.append(f"  - Color {color} at ~({qr},{qc})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Trigger hypothesis tracking
    # ------------------------------------------------------------------

    def check_trigger_correlation(
        self,
        step_num: int,
        player_pos: tuple[int, int],
        transformation_events: list,
        nearby_objects: list[tuple[int, int, str, int]],
    ) -> list[tuple[int, int, int]]:
        """Check if a transformation was caused by stepping on a special object.

        Args:
            step_num: Current step number.
            player_pos: Player position when the transformation occurred.
            transformation_events: List of TransformationEvent from the detector.
            nearby_objects: List of (center_r, center_c, shape, color) tuples
                           for objects near the player.

        Returns:
            List of (color, row, col) for objects identified as triggers,
            so the caller can mark them in inventory.
        """
        triggered: list[tuple[int, int, int]] = []

        # Filter to special shapes only
        special = [
            (r, c, shape, color)
            for r, c, shape, color in nearby_objects
            if shape in self._TRIGGER_SHAPES
        ]
        if not special or not transformation_events:
            return triggered

        for obj_r, obj_c, shape, color in special:
            for event in transformation_events:
                effect_type = event.transform_type.value
                pattern_key = (shape, color, effect_type)

                # Check if this matches an existing hypothesis/pattern
                if pattern_key in self._trigger_patterns:
                    # Strengthen existing pattern
                    existing = self._trigger_patterns[pattern_key]
                    existing.confidence += 1
                    logger.info(
                        "Trigger CONFIRMED (x%d): %s (color %d) at (%d,%d) -> %s",
                        existing.confidence, shape, color, obj_r, obj_c,
                        event.description,
                    )
                else:
                    # Create new hypothesis
                    hyp = TriggerHypothesis(
                        step=step_num,
                        trigger_pos=(obj_r, obj_c),
                        trigger_shape=shape,
                        trigger_color=color,
                        effect_type=effect_type,
                        effect_region=event.region,
                        effect_description=event.description,
                        confidence=1,
                    )
                    self._trigger_hypotheses.append(hyp)
                    self._trigger_patterns[pattern_key] = hyp
                    logger.info(
                        "Trigger HYPOTHESIS: stepping on %s (color %d) at (%d,%d) "
                        "caused: %s",
                        shape, color, obj_r, obj_c, event.description,
                    )

                triggered.append((color, obj_r, obj_c))
                # Record activation count and effect for tracking
                qr = (obj_r // STEP_SIZE) * STEP_SIZE
                qc = (obj_c // STEP_SIZE) * STEP_SIZE
                prev_count, prev_score = self._trigger_activations.get((qr, qc), (0, 0))
                self._trigger_activations[(qr, qc)] = (prev_count + 1, prev_score)
                self._trigger_effect_log.setdefault((qr, qc), []).append(
                    (step_num, event.description)
                )

        return triggered

    _TRIGGER_BLOCK_THRESHOLD = 3  # block after N fruitless activations

    def is_triggered_position(self, row: int, col: int, current_score: int = 0) -> bool:
        """Check if a trigger has been activated too many times without scoring.

        Returns True only if the trigger was activated >= threshold times
        and the score hasn't increased since the first activation.
        """
        qr = (row // STEP_SIZE) * STEP_SIZE
        qc = (col // STEP_SIZE) * STEP_SIZE
        if (qr, qc) not in self._trigger_activations:
            return False
        count, score_at_first = self._trigger_activations[(qr, qc)]
        # Block only if activated enough times AND score hasn't improved
        return count >= self._TRIGGER_BLOCK_THRESHOLD and current_score <= score_at_first

    def update_trigger_score(self, current_score: int) -> None:
        """Update stored scores for trigger positions after a score change.

        Call this when the score increases so triggers can be re-activated.
        """
        for pos in list(self._trigger_activations):
            count, _ = self._trigger_activations[pos]
            self._trigger_activations[pos] = (count, current_score)

    def get_trigger_hypotheses_summary(self) -> str:
        """Format trigger hypotheses/patterns for prompt injection."""
        if not self._trigger_hypotheses and not self._trigger_patterns:
            return ""

        lines: list[str] = ["# TRIGGER MECHANISMS (causal hypotheses)"]

        # Confirmed patterns first (confidence >= 2)
        confirmed = [
            h for h in self._trigger_patterns.values() if h.confidence >= 2
        ]
        if confirmed:
            lines.append("## Confirmed triggers:")
            for h in sorted(confirmed, key=lambda x: -x.confidence):
                lines.append(
                    f"  CONFIRMED (x{h.confidence}): Stepping on "
                    f"{h.trigger_shape.upper()} (color {h.trigger_color}) "
                    f"causes: {h.effect_description}"
                )
                if h.effect_region:
                    r1, c1, r2, c2 = h.effect_region
                    lines.append(
                        f"    Effect region: ({r1},{c1})-({r2},{c2})"
                    )

        # Unconfirmed hypotheses (confidence == 1)
        unconfirmed = [
            h for h in self._trigger_patterns.values() if h.confidence == 1
        ]
        if unconfirmed:
            lines.append("## Unconfirmed hypotheses (test by stepping on similar objects):")
            for h in unconfirmed:
                lines.append(
                    f"  HYPOTHESIS: Stepping on {h.trigger_shape.upper()} "
                    f"(color {h.trigger_color}) at ({h.trigger_pos[0]},"
                    f"{h.trigger_pos[1]}) may cause: {h.effect_description}"
                )
                lines.append(
                    f"    -> Find another {h.trigger_shape} and step on it "
                    f"to confirm this trigger"
                )

        if confirmed or unconfirmed:
            lines.append(
                "NOTE: Some triggers need multiple activations to have full effect. "
                "Others are reversible — stepping again may undo the effect."
            )
            lines.append(
                "STRATEGY: After activating a trigger, check the AFFECTED REGION "
                "for changes. If nothing useful happened, try activating again "
                "or explore elsewhere."
            )

        # Show activation history with effect details
        if self._trigger_activations:
            lines.append("")
            lines.append("## TRIGGER ACTIVATION HISTORY:")
            for (qr, qc), (count, _) in sorted(self._trigger_activations.items()):
                if count >= self._TRIGGER_BLOCK_THRESHOLD:
                    status = "exhausted — try something else"
                else:
                    status = "may need more activations"
                lines.append(
                    f"  - ({qr},{qc}): activated {count}x ({status})"
                )
                # Show effect progression so model can reason about pattern
                effects = self._trigger_effect_log.get((qr, qc), [])
                for step, desc in effects[-3:]:  # show last 3 effects
                    lines.append(f"      step {step}: {desc}")

        return "\n".join(lines)

    def _find_disappeared_near_player(
        self,
        prev_grid: list[list[int]],
        curr_grid: list[list[int]],
        player_pos: Optional[tuple[int, int]],
        search_radius: int = 15,
    ) -> list[tuple[int, int, tuple[int, int]]]:
        """Find clusters of cells that disappeared near the player.

        Returns list of (color, center_position).
        """
        if player_pos is None:
            return []

        H = len(prev_grid)
        W = len(prev_grid[0]) if H > 0 else 0
        pr, pc = player_pos

        # Detect background colors
        prev_bg = _quick_bg(prev_grid, H, W)
        curr_bg = _quick_bg(curr_grid, H, W)
        bg_colors = {prev_bg, curr_bg, self._energy_color}

        # Find cells that were non-bg and are now bg (or different)
        disappeared_cells: dict[int, list[tuple[int, int]]] = {}

        r_min = max(0, pr - search_radius)
        r_max = min(H, pr + search_radius)
        c_min = max(0, pc - search_radius)
        c_max = min(W, pc + search_radius)

        for r in range(r_min, r_max):
            for c in range(c_min, c_max):
                pv = prev_grid[r][c]
                cv = curr_grid[r][c]
                if pv != cv and pv not in bg_colors and cv in bg_colors:
                    disappeared_cells.setdefault(pv, []).append((r, c))

        results: list[tuple[int, tuple[int, int]]] = []
        for color, cells in disappeared_cells.items():
            if len(cells) < 2:
                continue  # Skip single-pixel noise
            # Compute center
            avg_r = sum(r for r, c in cells) // len(cells)
            avg_c = sum(c for r, c in cells) // len(cells)
            results.append((color, (avg_r, avg_c)))

        return results

    def _find_appeared(
        self,
        prev_grid: list[list[int]],
        curr_grid: list[list[int]],
        player_pos: Optional[tuple[int, int]],
    ) -> list[tuple[int, tuple[int, int]]]:
        """Find clusters of cells that appeared (not near player = not player movement)."""
        H = len(prev_grid)
        W = len(prev_grid[0]) if H > 0 else 0

        prev_bg = _quick_bg(prev_grid, H, W)
        curr_bg = _quick_bg(curr_grid, H, W)
        bg_colors = {prev_bg, curr_bg, self._energy_color}

        # Find cells that were bg and are now non-bg
        appeared_cells: dict[int, list[tuple[int, int]]] = {}

        for r in range(H):
            for c in range(W):
                pv = prev_grid[r][c]
                cv = curr_grid[r][c]
                if pv != cv and pv in bg_colors and cv not in bg_colors:
                    appeared_cells.setdefault(cv, []).append((r, c))

        results: list[tuple[int, tuple[int, int]]] = []
        for color, cells in appeared_cells.items():
            if len(cells) < 5:
                continue  # Skip small noise / player trail

            avg_r = sum(r for r, c in cells) // len(cells)
            avg_c = sum(c for r, c in cells) // len(cells)

            # Skip if it's near the player (likely player movement artifact)
            if player_pos is not None:
                dist = abs(avg_r - player_pos[0]) + abs(avg_c - player_pos[1])
                if dist < 10:
                    continue

            results.append((color, (avg_r, avg_c)))

        return results

    def _detect_energy_bar(self, grid: list[list[int]]) -> Optional[int]:
        """Detect energy bar length by scanning bottom rows.

        Returns the number of energy-colored cells in the energy row,
        or None if no energy bar detected.
        """
        H = len(grid)
        W = len(grid[0]) if H > 0 else 0
        if H < 3 or W < 10:
            return None

        # Scan bottom 3 rows for a horizontal bar of the energy color
        for row_idx in range(H - 1, max(H - 4, -1), -1):
            count = 0
            for c in range(W):
                if grid[row_idx][c] == self._energy_color:
                    count += 1
            if count > 10:  # Minimum bar length
                self._energy_row = row_idx
                return count

        return None

    def _update_rule(
        self,
        color: int,
        effect: str,
        energy_delta: int,
        score_delta: int,
    ) -> None:
        """Create or update an interaction rule."""
        key = color
        if key in self._rules:
            rule = self._rules[key]
            n = rule.confidence
            rule.confidence = n + 1
            # Running average
            rule.avg_energy_delta = (
                rule.avg_energy_delta * n + energy_delta
            ) / (n + 1)
            rule.avg_score_delta = (
                rule.avg_score_delta * n + score_delta
            ) / (n + 1)
            # Update effect if stronger signal
            if effect == "score_increase" or (
                effect == "energy_refill" and rule.effect != "score_increase"
            ):
                rule.effect = effect
        else:
            self._rules[key] = InteractionRule(
                trigger_color=color,
                effect=effect,
                confidence=1,
                avg_energy_delta=float(energy_delta),
                avg_score_delta=float(score_delta),
            )

    def get_rules_summary(self) -> str:
        """Format learned rules for prompt injection."""
        if not self._rules:
            return ""
        lines: list[str] = ["# INTERACTION RULES (learned from gameplay)"]
        for rule in sorted(
            self._rules.values(), key=lambda r: r.confidence, reverse=True
        ):
            lines.append(f"  {rule.describe()}")
        return "\n".join(lines)

    def get_recent_events(self, n: int = 3) -> str:
        """Format last N interaction events."""
        if not self._events:
            return ""
        recent = self._events[-n:]
        lines: list[str] = ["# RECENT INTERACTIONS"]
        for ev in recent:
            lines.append(f"  Step {ev.step}: {ev.description}")
        return "\n".join(lines)

    def get_rules(self) -> dict[int, InteractionRule]:
        """Return the learned rules (for ObjectInventory to use)."""
        return self._rules

    def reset(self) -> None:
        """Reset events but keep rules, toggle positions, and trigger patterns (persist across retries)."""
        self._events.clear()
        self._last_energy_length = None
        self._toggle_history.clear()
        self._trigger_hypotheses.clear()
        # _toggle_positions, _rules, and _trigger_patterns are kept across retries


# =============================================================================
# Module C: ObjectInventory -- Systematic Exploration Planning
# =============================================================================


class ObjectStatus(Enum):
    LOCATED = "LOCATED"
    VISITED = "VISITED"
    COLLECTED = "COLLECTED"
    GOAL = "GOAL"


@dataclass
class InventoryItem:
    """A tracked interactive object."""

    color: int
    position: tuple[int, int]  # (row, col) center
    size: int
    status: ObjectStatus = ObjectStatus.LOCATED
    role: str = "unknown"  # "energy", "prerequisite", "goal", "wall", "floor"
    shape: str = "unknown"  # geometric shape: cross, diamond, rect, etc.
    distance_actions: float = 999.0
    priority: int = 0  # lower = higher priority
    visits: int = 0  # consecutive analysis cycles with player nearby
    total_visits: int = 0  # cumulative visits (never resets)

    def describe(self) -> str:
        status_icon = {
            ObjectStatus.LOCATED: "[ ]",
            ObjectStatus.VISITED: "[~]",
            ObjectStatus.COLLECTED: "[x]",
            ObjectStatus.GOAL: "[G]",
        }
        icon = status_icon.get(self.status, "[?]")
        dist_str = (
            f"~{self.distance_actions:.0f} actions"
            if self.distance_actions < 900
            else "unknown dist"
        )
        shape_str = ""
        if self.shape and self.shape not in ("unknown", "rect", "point", "irregular"):
            shape_str = f" **{self.shape.upper()} SHAPE**"
        return (
            f"{icon} color {self.color} at ({self.position[0]},{self.position[1]}) "
            f"[{self.role}]{shape_str} {dist_str}"
        )


class ObjectInventory:
    """Track all interactive objects and suggest next target.

    Classifies objects as wall/floor/player/interactive based on size,
    color, and interaction rules from the InteractionTracker.
    """

    def __init__(self) -> None:
        self._items: list[InventoryItem] = []
        # Colors classified as non-interactive
        self._wall_colors: set[int] = set()
        self._floor_colors: set[int] = set()
        self._player_colors: set[int] = set()
        self._ui_colors: set[int] = set()
        # Track which colors have been collected (from InteractionTracker)
        self._collected_colors: set[int] = set()

    def update_from_analysis(
        self,
        objects: list,
        bg_color: int,
        player_pos: Optional[tuple[int, int]],
        player_colors: set[int],
        step: int,
        interaction_rules: dict[int, InteractionRule],
    ) -> None:
        """Classify objects and update inventory.

        Args:
            objects: List of GridObject from analysis.
            bg_color: Background/floor color.
            player_pos: Current player position (row, col).
            player_colors: Colors that are part of the player entity.
            step: Current step number.
            interaction_rules: Learned rules from InteractionTracker.
        """
        self._floor_colors.add(bg_color)
        prev_player_colors = set(self._player_colors)
        self._player_colors.update(player_colors)

        # Fix 3: Delayed reclassification — if player_colors grew, purge
        # inventory items that were mistakenly added before we knew they
        # belonged to the player.
        new_player_colors = self._player_colors - prev_player_colors
        if new_player_colors:
            before = len(self._items)
            self._items = [
                item for item in self._items
                if item.color not in new_player_colors
            ]
            if len(self._items) < before:
                logger.info(
                    "ObjectInventory: purged %d items for newly-identified "
                    "player colors %s",
                    before - len(self._items),
                    sorted(new_player_colors),
                )

        # Build a set of existing item positions for matching
        existing_positions: dict[tuple[int, int, int], InventoryItem] = {}
        for item in self._items:
            key = (item.color, item.position[0] // STEP_SIZE, item.position[1] // STEP_SIZE)
            existing_positions[key] = item

        # Distance threshold: player-colored objects THIS far from the
        # player are treated as separate game elements, not the player.
        _REMOTE_PLAYER_COLOR_DIST = 20  # 4 steps away

        for obj in objects:
            # Skip background, UI elements
            if obj.color == bg_color:
                continue
            if obj.color in self._ui_colors:
                continue

            # Player-color filter: skip objects that are near the player
            # (they are likely part of the player entity).  But keep
            # player-colored objects that are FAR from the player —
            # they could be goal markers or targets in a different area.
            if obj.color in self._player_colors:
                if player_pos is None:
                    continue
                dist_r = abs(int(obj.center_r) - player_pos[0])
                dist_c = abs(int(obj.center_c) - player_pos[1])
                if dist_r + dist_c < _REMOTE_PLAYER_COLOR_DIST:
                    continue
                # Remote player-colored object — treat as potential goal
                logger.info(
                    "ObjectInventory: remote player-color %d at (%d,%d) "
                    "dist=%d — treating as potential goal",
                    obj.color,
                    int(obj.center_r),
                    int(obj.center_c),
                    dist_r + dist_c,
                )

            # Fix 2: Position filtering — small objects overlapping the player
            # are almost certainly part of the player entity, not collectibles.
            # Only active in the first few steps: later in the game, new objects
            # near the player are likely game events (spawns, color changes),
            # not undiscovered player body parts.  After early steps, Fix 1
            # (movement correlation) and Fix 3 (delayed reclassification)
            # handle player color detection.
            if (
                step <= 3
                and player_pos is not None
                and obj.size < 50
                and abs(int(obj.center_r) - player_pos[0]) <= STEP_SIZE
                and abs(int(obj.center_c) - player_pos[1]) <= STEP_SIZE
            ):
                self._player_colors.add(obj.color)
                logger.info(
                    "ObjectInventory: learned player color %d via proximity "
                    "(early step %d)",
                    obj.color, step,
                )
                continue

            # Skip very large objects (walls/borders)
            if obj.size > 200:
                self._wall_colors.add(obj.color)
                continue

            # Skip objects at the bottom edge (UI elements like energy bar)
            if obj.bbox[2] >= 60:  # Bottom 4 rows
                self._ui_colors.add(obj.color)
                continue

            # Check if this matches an existing item
            center = (int(obj.center_r), int(obj.center_c))
            key = (obj.color, center[0] // STEP_SIZE, center[1] // STEP_SIZE)
            if key in existing_positions:
                # Update position if slightly moved
                existing_positions[key].position = center
                existing_positions[key].size = obj.size
                continue

            # Classify role based on interaction rules
            role = "unknown"
            if obj.color in interaction_rules:
                rule = interaction_rules[obj.color]
                if rule.effect == "energy_refill":
                    role = "energy"
                elif rule.effect == "score_increase":
                    role = "goal"
                else:
                    role = "prerequisite"
            elif obj.color in self._player_colors:
                # Remote player-colored object (passed distance filter above)
                role = "goal"
            elif obj.color in self._collected_colors:
                role = "prerequisite"
            elif obj.shape in ("cross", "diamond", "T-shape"):
                role = "prerequisite"  # Geometric shapes are likely interactive
            elif obj.size < 30 and obj.shape in ("point", "rect", "irregular"):
                role = "prerequisite"  # Small objects are likely collectibles

            # Don't add items for wall colors
            if obj.color in self._wall_colors:
                continue

            # Cross/diamond shapes get higher priority
            priority = 0
            if obj.shape in ("cross", "diamond", "T-shape"):
                priority = -10  # Higher priority (lower number)

            self._items.append(InventoryItem(
                color=obj.color,
                position=center,
                size=obj.size,
                status=ObjectStatus.LOCATED,
                role=role,
                shape=obj.shape,
                priority=priority,
            ))

    def mark_collected(self, color: int, position: tuple[int, int]) -> None:
        """Mark an item as collected based on InteractionTracker events."""
        self._collected_colors.add(color)
        best_item: Optional[InventoryItem] = None
        best_dist = float("inf")

        for item in self._items:
            if item.color != color or item.status == ObjectStatus.COLLECTED:
                continue
            dist = abs(item.position[0] - position[0]) + abs(
                item.position[1] - position[1]
            )
            if dist < best_dist:
                best_dist = dist
                best_item = item

        if best_item is not None:
            best_item.status = ObjectStatus.COLLECTED
            logger.info(
                "ObjectInventory: marked color %d at (%d,%d) as COLLECTED",
                color, best_item.position[0], best_item.position[1],
            )

    # How many analysis cycles near an item before marking VISITED
    _VISIT_THRESHOLD: int = 2

    def update_distances(
        self,
        player_pos: Optional[tuple[int, int]],
        navigator: Optional[GridNavigator] = None,
    ) -> None:
        """Compute action distances from player to each item.

        Also tracks how long the player has been near each item.
        If the player stays near an item for ``_VISIT_THRESHOLD`` analysis
        cycles without the item being collected, mark it as VISITED so
        ``get_next_target`` moves on.
        """
        if player_pos is None:
            return

        for item in self._items:
            if item.status == ObjectStatus.COLLECTED:
                item.distance_actions = 0
                continue

            if navigator is not None and navigator._dir_to_action:
                # Use BFS path length
                path = navigator.navigate_to(
                    item.position[0],
                    item.position[1],
                    player_pos[0],
                    player_pos[1],
                    max_steps=30,
                    log=False,
                )
                if path is not None:
                    item.distance_actions = float(len(path))
                else:
                    # BFS couldn't find path — use Manhattan fallback
                    dr = abs(item.position[0] - player_pos[0])
                    dc = abs(item.position[1] - player_pos[1])
                    item.distance_actions = (dr + dc) / STEP_SIZE
            else:
                # Fallback: Manhattan distance / step_size
                dr = abs(item.position[0] - player_pos[0])
                dc = abs(item.position[1] - player_pos[1])
                item.distance_actions = (dr + dc) / STEP_SIZE

            # --- Visit tracking ---
            # Player is "at" the item when within one step
            dr = abs(item.position[0] - player_pos[0])
            dc = abs(item.position[1] - player_pos[1])
            if dr <= STEP_SIZE and dc <= STEP_SIZE:
                item.visits += 1
                item.total_visits += 1
                if (
                    (item.visits >= self._VISIT_THRESHOLD or item.total_visits >= 4)
                    and item.status == ObjectStatus.LOCATED
                ):
                    item.status = ObjectStatus.VISITED
                    logger.info(
                        "ObjectInventory: marked color %d at (%d,%d) as "
                        "VISITED (nearby %d consecutive / %d total, not interactive)",
                        item.color,
                        item.position[0],
                        item.position[1],
                        item.visits,
                        item.total_visits,
                    )
            else:
                # Reset consecutive counter when player moves away
                item.visits = 0

    def get_next_target(
        self, current_energy: Optional[int] = None
    ) -> Optional[InventoryItem]:
        """Suggest the next target based on priority.

        Priority: energy refills (if low) > prerequisites (nearest) > goal
        """
        active = [
            item for item in self._items
            if item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
        ]
        if not active:
            return None

        # Separate by role
        energy_items = [i for i in active if i.role == "energy"]
        prereqs = [i for i in active if i.role == "prerequisite"]
        goals = [i for i in active if i.role == "goal"]
        unknowns = [i for i in active if i.role == "unknown"]

        # If energy is low, prioritize energy refills
        if current_energy is not None and current_energy < 30 and energy_items:
            return min(energy_items, key=lambda i: i.distance_actions)

        # Collect prerequisites first (nearest first)
        if prereqs:
            return min(prereqs, key=lambda i: i.distance_actions)

        # Unknowns (explore them)
        if unknowns:
            return min(unknowns, key=lambda i: i.distance_actions)

        # Goal (only after all prerequisites collected)
        if goals:
            return min(goals, key=lambda i: i.distance_actions)

        # Energy items as last resort
        if energy_items:
            return min(energy_items, key=lambda i: i.distance_actions)

        return None

    def get_inventory_summary(self) -> str:
        """Format inventory for prompt injection."""
        if not self._items:
            return ""

        active = [
            i for i in self._items
            if i.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
        ]
        collected = [i for i in self._items if i.status == ObjectStatus.COLLECTED]
        visited = [i for i in self._items if i.status == ObjectStatus.VISITED]

        lines: list[str] = ["# OBJECT INVENTORY"]

        if collected:
            lines.append(f"Collected: {len(collected)}")

        if visited:
            lines.append(f"Visited (not interactive): {len(visited)}")

        if active:
            sorted_active = sorted(active, key=lambda i: i.distance_actions)
            lines.append(f"Remaining: {len(active)} items (nearest first):")
            for item in sorted_active[:5]:
                lines.append(f"  {item.describe()}")
            if len(sorted_active) > 5:
                lines.append(f"  +{len(sorted_active) - 5} more")

        target = self.get_next_target()
        if target:
            lines.append(
                f"=> Next: c{target.color} at ({target.position[0]},{target.position[1]}) "
                f"[{target.role}] — use navigate_to({target.position[0]},{target.position[1]})"
            )
        elif self._items and not active:
            lines.append(
                "All objects visited/collected. Explore NEW areas with navigate_to."
            )

        return "\n".join(lines)

    def reset(self, keep_classifications: bool = True) -> None:
        """Reset items but optionally keep color classifications."""
        self._items.clear()
        if not keep_classifications:
            self._wall_colors.clear()
            self._floor_colors.clear()
            self._player_colors.clear()
            self._ui_colors.clear()
            self._collected_colors.clear()


# =============================================================================
# Helper
# =============================================================================


def _quick_bg(grid: list[list[int]], H: int, W: int) -> int:
    """Fast background detection via sampling."""
    counts: dict[int, int] = {}
    for r in (0, H // 4, H // 2, 3 * H // 4, H - 1):
        for c in (0, W // 4, W // 2, 3 * W // 4, W - 1):
            if 0 <= r < H and 0 <= c < W:
                counts[grid[r][c]] = counts.get(grid[r][c], 0) + 1
    if H > 0:
        for v in grid[0]:
            counts[v] = counts.get(v, 0) + 1
        for v in grid[H - 1]:
            counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get) if counts else 0


# =============================================================================
# Module D: TransformationDetector -- Grid Transformation Analysis
# =============================================================================


class TransformationType(Enum):
    """Types of grid transformations detected algorithmically."""

    ROTATION_90 = "ROTATION_90"
    ROTATION_180 = "ROTATION_180"
    ROTATION_270 = "ROTATION_270"
    MIRROR_H = "MIRROR_H"  # horizontal flip (left-right)
    MIRROR_V = "MIRROR_V"  # vertical flip (top-bottom)
    COLOR_MAP = "COLOR_MAP"  # systematic color substitution
    SHIFT = "SHIFT"  # translation of a pattern


@dataclass
class TransformationEvent:
    """A detected grid transformation."""

    step: int
    transform_type: TransformationType
    description: str
    region: Optional[tuple[int, int, int, int]] = None  # (r1, c1, r2, c2)
    color_map: Optional[dict[int, int]] = None
    shift_delta: Optional[tuple[int, int]] = None


class TransformationDetector:
    """Detects common grid transformations from consecutive frames.

    Zero LLM cost — purely algorithmic comparison of grid states.
    Detects: rotations (90/180/270), reflections (H/V),
    color mappings, and pattern shifts.
    """

    # Minimum changed cells to consider (filter noise from energy bar etc.)
    _MIN_CHANGES: int = 10
    # Maximum region dimension to test spatial transforms (perf guard)
    _MAX_REGION: int = 30
    # Max clusters to analyze per step
    _MAX_CLUSTERS: int = 5
    # Cells around player to exclude (covers old + new position after 1 step)
    _PLAYER_MARGIN: int = 12
    # UI rows at bottom of grid to exclude (energy bar, score)
    _UI_BOTTOM_ROWS: int = 4

    def __init__(self) -> None:
        self._history: list[TransformationEvent] = []
        # Persistent: (action, quantized_pos) -> list of observed transforms
        self._learned_rules: dict[
            tuple[str, tuple[int, int]], list[TransformationType]
        ] = {}
        # Post-trigger impact analysis results (latest)
        self._latest_impact: str = ""

    def analyze_step(
        self,
        step_num: int,
        prev_grid: Optional[list[list[int]]],
        curr_grid: Optional[list[list[int]]],
        player_pos: Optional[tuple[int, int]] = None,
        action: str = "",
    ) -> list[TransformationEvent]:
        """Detect transformations between two consecutive grid states.

        Args:
            step_num: Current step number.
            prev_grid: Grid before the action.
            curr_grid: Grid after the action.
            player_pos: (row, col) of player center — excluded from analysis.
            action: The action that was taken (for learning rules).

        Returns:
            List of detected TransformationEvents.
        """
        events: list[TransformationEvent] = []
        if prev_grid is None or curr_grid is None:
            return events

        H = len(prev_grid)
        W = len(prev_grid[0]) if H > 0 else 0
        if H < 4 or W < 4:
            return events

        # 1. Find changed cells (exclude player area + UI rows)
        ui_rows = set(range(max(0, H - self._UI_BOTTOM_ROWS), H))
        changed = self._find_changed(
            prev_grid, curr_grid, H, W, player_pos, ui_rows
        )
        if len(changed) < self._MIN_CHANGES:
            return events

        # 2. Color mapping (global check across all changed cells)
        cm_event = self._check_color_map(
            step_num, prev_grid, curr_grid, changed
        )
        if cm_event:
            events.append(cm_event)

        # 3. Cluster changed cells, merge nearby clusters, test transforms
        clusters = self._cluster(changed)
        merged = self._merge_nearby_clusters(clusters, gap=2)
        for cells in merged[: self._MAX_CLUSTERS]:
            r1, c1, r2, c2 = self._bbox(cells)
            h, w = r2 - r1, c2 - c1
            if h > self._MAX_REGION or w > self._MAX_REGION:
                continue
            if h < 3 or w < 3:
                continue

            prev_r = self._extract(prev_grid, r1, c1, r2, c2)
            curr_r = self._extract(curr_grid, r1, c1, r2, c2)
            if prev_r == curr_r:
                continue

            ev = self._test_spatial(step_num, prev_r, curr_r, r1, c1, r2, c2)
            if ev:
                events.append(ev)

        # 4. Shift detection (pattern translated by STEP_SIZE)
        shift_ev = self._check_shift(
            step_num, prev_grid, curr_grid, changed, H, W
        )
        if shift_ev:
            events.append(shift_ev)

        # Record
        self._history.extend(events)

        # Learn: associate (action, position) -> transform type
        if events and action and player_pos:
            qr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (player_pos[1] // STEP_SIZE) * STEP_SIZE
            key = (action, (qr, qc))
            self._learned_rules.setdefault(key, []).extend(
                ev.transform_type for ev in events
            )

        if events:
            for ev in events:
                logger.info("Transformation detected at step %d: %s", step_num, ev.description)

        return events

    # ------------------------------------------------------------------ #
    # Changed-cell detection
    # ------------------------------------------------------------------ #

    def _find_changed(
        self,
        prev: list[list[int]],
        curr: list[list[int]],
        H: int,
        W: int,
        player_pos: Optional[tuple[int, int]],
        ui_rows: set[int],
    ) -> list[tuple[int, int]]:
        """Find cells that differ, excluding player area and UI."""
        changed: list[tuple[int, int]] = []
        # Player exclusion zone
        if player_pos:
            pr, pc = player_pos
            pr1 = pr - self._PLAYER_MARGIN
            pr2 = pr + self._PLAYER_MARGIN
            pc1 = pc - self._PLAYER_MARGIN
            pc2 = pc + self._PLAYER_MARGIN
        else:
            pr1 = pr2 = pc1 = pc2 = -1

        for r in range(H):
            if r in ui_rows:
                continue
            prev_row = prev[r]
            curr_row = curr[r]
            for c in range(W):
                if pr1 <= r <= pr2 and pc1 <= c <= pc2:
                    continue
                if prev_row[c] != curr_row[c]:
                    changed.append((r, c))
        return changed

    # ------------------------------------------------------------------ #
    # Clustering
    # ------------------------------------------------------------------ #

    def _cluster(
        self, cells: list[tuple[int, int]]
    ) -> list[list[tuple[int, int]]]:
        """Group changed cells into 8-connected clusters."""
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

        clusters.sort(key=len, reverse=True)
        return clusters

    @staticmethod
    def _merge_nearby_clusters(
        clusters: list[list[tuple[int, int]]], gap: int = 2
    ) -> list[list[tuple[int, int]]]:
        """Merge clusters whose bounding boxes are within *gap* cells.

        Handles transforms with fixed axes (e.g., mirror with unchanged
        center column splitting changed cells into separate clusters).
        """
        if len(clusters) <= 1:
            return clusters

        # Compute bounding boxes
        def bbox(cl: list[tuple[int, int]]) -> tuple[int, int, int, int]:
            rs = [c[0] for c in cl]
            cs = [c[1] for c in cl]
            return min(rs), min(cs), max(rs) + 1, max(cs) + 1

        boxes = [bbox(c) for c in clusters]
        n = len(clusters)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n):
            for j in range(i + 1, n):
                r1a, c1a, r2a, c2a = boxes[i]
                r1b, c1b, r2b, c2b = boxes[j]
                # Check if bboxes overlap or are within gap
                if (
                    r1a - gap <= r2b
                    and r2a + gap >= r1b
                    and c1a - gap <= c2b
                    and c2a + gap >= c1b
                ):
                    union(i, j)

        # Group by root
        groups: dict[int, list[tuple[int, int]]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).extend(clusters[i])

        merged = list(groups.values())
        merged.sort(key=len, reverse=True)
        return merged

    @staticmethod
    def _bbox(
        cells: list[tuple[int, int]],
    ) -> tuple[int, int, int, int]:
        """Bounding box (r1, c1, r2, c2) — r2/c2 exclusive."""
        rs = [c[0] for c in cells]
        cs = [c[1] for c in cells]
        return min(rs), min(cs), max(rs) + 1, max(cs) + 1

    @staticmethod
    def _extract(
        grid: list[list[int]], r1: int, c1: int, r2: int, c2: int
    ) -> list[list[int]]:
        """Extract sub-region grid[r1:r2, c1:c2]."""
        return [row[c1:c2] for row in grid[r1:r2]]

    # ------------------------------------------------------------------ #
    # Spatial transform tests
    # ------------------------------------------------------------------ #

    def _test_spatial(
        self,
        step: int,
        prev_r: list[list[int]],
        curr_r: list[list[int]],
        r1: int,
        c1: int,
        r2: int,
        c2: int,
    ) -> Optional[TransformationEvent]:
        """Test a region for rotation / mirror transforms."""
        h = r2 - r1
        w = c2 - c1
        tag = f"({r1},{c1})-({r2},{c2})"

        # 180° rotation (works for any dimensions)
        if self._eq(self._rot180(prev_r), curr_r):
            return TransformationEvent(
                step=step,
                transform_type=TransformationType.ROTATION_180,
                description=f"180° rotation in region {tag}",
                region=(r1, c1, r2, c2),
            )

        # Horizontal mirror (flip left-right)
        if self._eq(self._mirror_h(prev_r), curr_r):
            return TransformationEvent(
                step=step,
                transform_type=TransformationType.MIRROR_H,
                description=f"Horizontal mirror in region {tag}",
                region=(r1, c1, r2, c2),
            )

        # Vertical mirror (flip top-bottom)
        if self._eq(self._mirror_v(prev_r), curr_r):
            return TransformationEvent(
                step=step,
                transform_type=TransformationType.MIRROR_V,
                description=f"Vertical mirror in region {tag}",
                region=(r1, c1, r2, c2),
            )

        # 90° / 270° rotation — only for square regions
        if h == w:
            if self._eq(self._rot90(prev_r), curr_r):
                return TransformationEvent(
                    step=step,
                    transform_type=TransformationType.ROTATION_90,
                    description=f"90° CW rotation in region {tag}",
                    region=(r1, c1, r2, c2),
                )
            if self._eq(self._rot270(prev_r), curr_r):
                return TransformationEvent(
                    step=step,
                    transform_type=TransformationType.ROTATION_270,
                    description=f"270° CW rotation in region {tag}",
                    region=(r1, c1, r2, c2),
                )

        return None

    # ------------------------------------------------------------------ #
    # Color mapping detection
    # ------------------------------------------------------------------ #

    def _check_color_map(
        self,
        step: int,
        prev: list[list[int]],
        curr: list[list[int]],
        changed: list[tuple[int, int]],
    ) -> Optional[TransformationEvent]:
        """Check if changed cells follow a consistent color→color mapping."""
        # Build mapping: old_color -> set of new_colors
        mapping: dict[int, set[int]] = {}
        for r, c in changed:
            old, new = prev[r][c], curr[r][c]
            if old == new:
                continue
            mapping.setdefault(old, set()).add(new)

        if not mapping:
            return None

        # Must be consistent: each old color -> exactly one new color
        consistent: dict[int, int] = {}
        for old, news in mapping.items():
            if len(news) != 1:
                return None
            consistent[old] = next(iter(news))

        if not consistent:
            return None

        # Verify it's not just noise — require enough cells for each mapping
        counts: dict[tuple[int, int], int] = {}
        for r, c in changed:
            pair = (prev[r][c], curr[r][c])
            if pair[0] != pair[1]:
                counts[pair] = counts.get(pair, 0) + 1

        # Each color pair must have at least 3 cells to be credible
        if any(cnt < 3 for cnt in counts.values()):
            return None

        desc_parts = [f"{o}→{n}" for o, n in sorted(consistent.items())]
        return TransformationEvent(
            step=step,
            transform_type=TransformationType.COLOR_MAP,
            description=(
                f"Color mapping: {', '.join(desc_parts)} "
                f"({len(changed)} cells affected)"
            ),
            color_map=consistent,
        )

    # ------------------------------------------------------------------ #
    # Shift detection
    # ------------------------------------------------------------------ #

    def _check_shift(
        self,
        step: int,
        prev: list[list[int]],
        curr: list[list[int]],
        changed: list[tuple[int, int]],
        H: int,
        W: int,
    ) -> Optional[TransformationEvent]:
        """Check if a pattern shifted by STEP_SIZE in any direction."""
        if len(changed) < self._MIN_CHANGES:
            return None

        # Collect (r, c, old_color) for cells that changed
        old_cells: list[tuple[int, int, int]] = []
        for r, c in changed:
            old_cells.append((r, c, prev[r][c]))

        best_delta: Optional[tuple[int, int]] = None
        best_ratio = 0.0
        best_count = 0

        # Test shifts by STEP_SIZE in 4 cardinal + 4 diagonal directions
        for dr, dc in [
            (0, STEP_SIZE),
            (0, -STEP_SIZE),
            (STEP_SIZE, 0),
            (-STEP_SIZE, 0),
            (STEP_SIZE, STEP_SIZE),
            (STEP_SIZE, -STEP_SIZE),
            (-STEP_SIZE, STEP_SIZE),
            (-STEP_SIZE, -STEP_SIZE),
        ]:
            match = 0
            total = 0
            for r, c, color in old_cells:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W:
                    total += 1
                    if curr[nr][nc] == color:
                        match += 1
            if total > 0:
                ratio = match / total
                if (
                    ratio > 0.7
                    and match >= self._MIN_CHANGES
                    and ratio > best_ratio
                ):
                    best_ratio = ratio
                    best_delta = (dr, dc)
                    best_count = match

        if best_delta:
            return TransformationEvent(
                step=step,
                transform_type=TransformationType.SHIFT,
                description=(
                    f"Pattern shifted by {best_delta} "
                    f"({best_count} cells matched, {best_ratio:.0%})"
                ),
                shift_delta=best_delta,
            )
        return None

    # ------------------------------------------------------------------ #
    # Matrix transform primitives
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rot90(m: list[list[int]]) -> list[list[int]]:
        """Rotate 90° clockwise."""
        h = len(m)
        w = len(m[0]) if h else 0
        return [[m[h - 1 - j][i] for j in range(h)] for i in range(w)]

    @staticmethod
    def _rot180(m: list[list[int]]) -> list[list[int]]:
        """Rotate 180°."""
        return [row[::-1] for row in reversed(m)]

    @staticmethod
    def _rot270(m: list[list[int]]) -> list[list[int]]:
        """Rotate 270° clockwise (= 90° counter-clockwise)."""
        h = len(m)
        w = len(m[0]) if h else 0
        return [[m[j][w - 1 - i] for j in range(h)] for i in range(w)]

    @staticmethod
    def _mirror_h(m: list[list[int]]) -> list[list[int]]:
        """Horizontal mirror (flip left↔right)."""
        return [row[::-1] for row in m]

    @staticmethod
    def _mirror_v(m: list[list[int]]) -> list[list[int]]:
        """Vertical mirror (flip top↔bottom)."""
        return list(reversed(m))

    @staticmethod
    def _eq(a: list[list[int]], b: list[list[int]]) -> bool:
        """Check if two 2D arrays are identical."""
        if len(a) != len(b):
            return False
        return all(ra == rb for ra, rb in zip(a, b))

    # ------------------------------------------------------------------ #
    # Post-trigger impact analysis
    # ------------------------------------------------------------------ #

    def analyze_transform_impact(
        self,
        prev_grid: list[list[int]],
        curr_grid: list[list[int]],
        events: list[TransformationEvent],
        bg_color: int,
    ) -> str:
        """Analyze what a transformation actually changed in gameplay terms.

        Checks:
        1. Did the transform change cells in a localized area?
        2. Did the transform align patterns between adjacent regions?
        3. Where should the agent go next to exploit the change?

        Returns a human-readable impact summary, or "" if no meaningful impact.
        """
        if not events:
            return ""

        H = len(prev_grid)
        W = len(prev_grid[0]) if H > 0 else 0
        # Exclude UI rows at bottom
        ui_cutoff = max(0, H - self._UI_BOTTOM_ROWS)
        parts: list[str] = []

        for event in events:
            if event.transform_type == TransformationType.COLOR_MAP and event.color_map:
                # Find ALL cells that changed due to this color mapping
                changed_cells: list[tuple[int, int]] = []
                for r in range(min(H, ui_cutoff)):
                    for c in range(W):
                        old_v = prev_grid[r][c]
                        new_v = curr_grid[r][c]
                        if old_v != new_v and old_v in event.color_map:
                            changed_cells.append((r, c))
                if changed_cells:
                    avg_r = sum(r for r, c in changed_cells) // len(changed_cells)
                    avg_c = sum(c for r, c in changed_cells) // len(changed_cells)
                    # Describe the mapping
                    map_str = ", ".join(
                        f"{o}→{n}" for o, n in event.color_map.items()
                    )
                    parts.append(
                        f"COLOR CHANGE: {len(changed_cells)} cells changed "
                        f"({map_str}) centered at ({avg_r},{avg_c}). "
                        f"This may have opened a path or aligned a pattern. "
                        f"Navigate to ({avg_r},{avg_c}) to investigate!"
                    )
                    logger.info(
                        "Transform impact: color map %s, %d cells changed near (%d,%d)",
                        map_str, len(changed_cells), avg_r, avg_c,
                    )

            elif event.transform_type == TransformationType.SHIFT and event.shift_delta:
                dr, dc = event.shift_delta
                parts.append(
                    f"PATTERN SHIFTED by ({dr},{dc}). "
                    f"A structure moved — check if it now aligns with "
                    f"another structure or opens a passage."
                )

            elif event.region:
                r1, c1, r2, c2 = event.region
                # For spatial transforms (rotation/mirror), check if the
                # transformed region now matches an adjacent region
                impact = self._check_region_alignment(
                    curr_grid, r1, c1, r2, c2, H, W, bg_color
                )
                if impact:
                    parts.append(impact)
                else:
                    mid_r = (r1 + r2) // 2
                    mid_c = (c1 + c2) // 2
                    parts.append(
                        f"REGION TRANSFORMED at ({r1},{c1})-({r2},{c2}). "
                        f"Navigate to ({mid_r},{mid_c}) to check if a "
                        f"path or entrance opened."
                    )

        result = "\n".join(parts)
        self._latest_impact = result
        return result

    def _check_region_alignment(
        self,
        grid: list[list[int]],
        r1: int,
        c1: int,
        r2: int,
        c2: int,
        H: int,
        W: int,
        bg_color: int,
    ) -> str:
        """Check if a region now aligns with an adjacent region.

        Compares the transformed region with regions above, below, left, right.
        If similarity is high (>70%), reports alignment — which often means
        a path or entrance has been created.
        """
        region = self._extract(grid, r1, c1, r2, c2)
        h = r2 - r1
        w = c2 - c1

        best_sim = 0.0
        best_dir = ""
        best_pos = (0, 0)

        # Check adjacent regions of the same size
        neighbors = [
            ("ABOVE", r1 - h, c1, r1, c2),
            ("BELOW", r2, c1, r2 + h, c2),
            ("LEFT", r1, c1 - w, r2, c1),
            ("RIGHT", r1, c2, r2, c2 + w),
        ]

        for direction, nr1, nc1, nr2, nc2 in neighbors:
            if nr1 < 0 or nc1 < 0 or nr2 > H or nc2 > W:
                continue
            neighbor = self._extract(grid, nr1, nc1, nr2, nc2)
            if len(neighbor) != len(region):
                continue
            if any(len(nr) != len(rr) for nr, rr in zip(neighbor, region)):
                continue

            # Compute similarity (ignoring bg cells in both)
            match = 0
            total = 0
            for rr, nr in zip(region, neighbor):
                for rv, nv in zip(rr, nr):
                    if rv == bg_color and nv == bg_color:
                        continue  # both bg, skip
                    total += 1
                    if rv == nv:
                        match += 1

            if total > 0:
                sim = match / total
                if sim > best_sim:
                    best_sim = sim
                    best_dir = direction
                    best_pos = ((nr1 + nr2) // 2, (nc1 + nc2) // 2)

        if best_sim > 0.7:
            return (
                f"PATTERN ALIGNED: Region ({r1},{c1})-({r2},{c2}) now "
                f"matches the region {best_dir} ({best_sim:.0%} similar). "
                f"This likely opened a passage! Navigate to ({best_pos[0]},"
                f"{best_pos[1]}) to enter."
            )
        return ""

    def get_latest_impact(self) -> str:
        """Return the latest transform impact analysis."""
        return self._latest_impact

    # ------------------------------------------------------------------ #
    # Prompt summary
    # ------------------------------------------------------------------ #

    def get_summary(self, last_n: int = 5) -> str:
        """Format recent transformations for prompt injection."""
        if not self._history:
            return ""
        recent = self._history[-last_n:]
        lines: list[str] = ["# DETECTED TRANSFORMATIONS"]
        for ev in recent:
            lines.append(f"  Step {ev.step}: {ev.description}")
            if ev.color_map:
                cm_str = ", ".join(
                    f"{o}→{n}" for o, n in sorted(ev.color_map.items())
                )
                lines.append(f"    Color map: {cm_str}")
        if self._learned_rules:
            lines.append("  Learned transform patterns:")
            for (act, pos), types in self._learned_rules.items():
                unique = sorted(set(t.value for t in types))
                lines.append(f"    {act} near {pos} -> {', '.join(unique)}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset history but keep learned rules (persist across retries)."""
        self._history.clear()


# =============================================================================
# Module E: RegionComparator -- Spatial similarity across regions in one grid
# =============================================================================


class RegionComparator:
    """Compare distinct regions within a single grid for spatial similarity.

    Finds bordered rectangular regions and tests spatial transforms between
    pairs. Purely algorithmic — zero LLM cost.
    """

    _MIN_BORDER_SIZE: int = 5   # minimum border side length (cells)
    _MAX_BORDER_SIZE: int = 30  # maximum border side length
    _SIMILARITY_THRESHOLD: float = 0.6  # minimum similarity to report

    def find_bordered_regions(
        self,
        grid: list[list[int]],
        bg_color: int,
        min_size: int = 5,
        max_size: int = 25,
    ) -> list[tuple[int, int, int, int, int]]:
        """Find rectangular areas bounded by a non-bg color (borders/frames).

        Scans for horizontal lines of same non-bg color, checks if they form
        a rectangle with vertical sides.

        Returns:
            List of (r1, c1, r2, c2, border_color) — the inner content region
            (exclusive r2, c2).
        """
        H = len(grid)
        W = len(grid[0]) if H > 0 else 0
        if H < min_size or W < min_size:
            return []

        regions: list[tuple[int, int, int, int, int]] = []
        seen: set[tuple[int, int, int, int]] = set()

        # Strategy: find horizontal line segments of uniform non-bg color,
        # then check if a matching bottom line + vertical sides exist.
        for r in range(H - min_size):
            c = 0
            while c < W - min_size:
                color = grid[r][c]
                if color == bg_color:
                    c += 1
                    continue

                # Find extent of horizontal line of this color
                c_end = c
                while c_end < W and grid[r][c_end] == color:
                    c_end += 1
                line_len = c_end - c

                if line_len < min_size or line_len > max_size:
                    c = c_end
                    continue

                # Try to find a matching bottom horizontal line
                for r2 in range(r + min_size, min(r + max_size + 1, H)):
                    # Check bottom line
                    if grid[r2][c] != color:
                        continue
                    bottom_end = c
                    while bottom_end < W and grid[r2][bottom_end] == color:
                        bottom_end += 1
                    if bottom_end - c < line_len:
                        continue

                    # Check left vertical side
                    left_ok = all(grid[rr][c] == color for rr in range(r, r2 + 1))
                    if not left_ok:
                        continue

                    # Check right vertical side (at c + line_len - 1)
                    right_c = c + line_len - 1
                    right_ok = all(grid[rr][right_c] == color for rr in range(r, r2 + 1))
                    if not right_ok:
                        continue

                    # We found a bordered rectangle!
                    # Inner region is (r+1, c+1) to (r2, right_c)
                    inner = (r + 1, c + 1, r2, right_c)
                    inner_h = inner[2] - inner[0]
                    inner_w = inner[3] - inner[1]
                    if inner_h < 3 or inner_w < 3:
                        continue
                    if inner in seen:
                        continue
                    seen.add(inner)
                    regions.append((inner[0], inner[1], inner[2], inner[3], color))

                c = c_end

        # Sort by area (largest first)
        regions.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)

        # Deduplicate overlapping regions (IoU > 0.5 → keep larger one)
        filtered: list[tuple[int, int, int, int, int]] = []
        for reg in regions:
            r1, c1, r2, c2, col = reg
            area = (r2 - r1) * (c2 - c1)
            overlap = False
            for fr1, fc1, fr2, fc2, _ in filtered:
                # Compute intersection
                ir1, ic1 = max(r1, fr1), max(c1, fc1)
                ir2, ic2 = min(r2, fr2), min(c2, fc2)
                inter = max(0, ir2 - ir1) * max(0, ic2 - ic1)
                if inter > 0.5 * area:
                    overlap = True
                    break
            if not overlap:
                filtered.append(reg)
        return filtered[:10]  # cap to avoid combinatorial explosion

    def compare_two_regions(
        self,
        grid: list[list[int]],
        region_a: tuple[int, int, int, int],
        region_b: tuple[int, int, int, int],
        bg_color: int,
    ) -> Optional[tuple[str, float]]:
        """Compare two grid regions for spatial similarity under transforms.

        Extracts sub-grids, normalizes by removing bg, and tests:
        identity, rot90, rot180, rot270, mirror_h, mirror_v.

        Returns:
            (transform_name, similarity_score) or None if no match > threshold.
        """
        r1a, c1a, r2a, c2a = region_a
        r1b, c1b, r2b, c2b = region_b

        sub_a = [row[c1a:c2a] for row in grid[r1a:r2a]]
        sub_b = [row[c1b:c2b] for row in grid[r1b:r2b]]

        if not sub_a or not sub_b:
            return None

        # Reuse TransformationDetector static methods
        _rot90 = TransformationDetector._rot90
        _rot180 = TransformationDetector._rot180
        _rot270 = TransformationDetector._rot270
        _mirror_h = TransformationDetector._mirror_h
        _mirror_v = TransformationDetector._mirror_v

        transforms: list[tuple[str, list[list[int]]]] = [
            ("identical", sub_a),
            ("180° rotation", _rot180(sub_a)),
            ("horizontal mirror", _mirror_h(sub_a)),
            ("vertical mirror", _mirror_v(sub_a)),
        ]

        # 90/270 only work if dimensions allow
        ha, wa = len(sub_a), len(sub_a[0]) if sub_a else 0
        hb, wb = len(sub_b), len(sub_b[0]) if sub_b else 0
        if ha == wb and wa == hb:
            transforms.append(("90° rotation", _rot90(sub_a)))
            transforms.append(("270° rotation", _rot270(sub_a)))

        best_name = ""
        best_score = 0.0

        for name, transformed in transforms:
            # Check dimension match
            if len(transformed) != len(sub_b):
                continue
            if any(len(tr) != len(br) for tr, br in zip(transformed, sub_b)):
                continue

            # Compute similarity ignoring bg in both
            match = 0
            total = 0
            for tr, br in zip(transformed, sub_b):
                for tv, bv in zip(tr, br):
                    if tv == bg_color and bv == bg_color:
                        continue
                    total += 1
                    if tv == bv:
                        match += 1

            if total > 0:
                sim = match / total
                if sim > best_score:
                    best_score = sim
                    best_name = name

        if best_score >= self._SIMILARITY_THRESHOLD:
            return (best_name, best_score)
        return None

    def find_similar_pairs(
        self,
        grid: list[list[int]],
        bg_color: int,
    ) -> list[str]:
        """Find pairs of bordered regions that are spatially similar.

        Returns list of human-readable descriptions.
        """
        regions = self.find_bordered_regions(grid, bg_color)
        if len(regions) < 2:
            return []

        descriptions: list[str] = []
        for i in range(len(regions)):
            for j in range(i + 1, len(regions)):
                ra = regions[i][:4]
                rb = regions[j][:4]
                result = self.compare_two_regions(grid, ra, rb, bg_color)
                if result:
                    name, score = result
                    descriptions.append(
                        f"Region ({ra[0]},{ra[1]})-({ra[2]},{ra[3]}) is "
                        f"{name} of region ({rb[0]},{rb[1]})-({rb[2]},{rb[3]}) "
                        f"({score:.0%} similar)"
                    )
        return descriptions

    def get_similarity_summary(
        self,
        grid: list[list[int]],
        bg_color: int,
    ) -> str:
        """Return formatted text for prompt injection."""
        pairs = self.find_similar_pairs(grid, bg_color)
        if not pairs:
            return ""
        lines = ["# REGION SIMILARITIES (algorithmic detection)"]
        for desc in pairs:
            lines.append(f"  - {desc}")
        lines.append(
            "These similar regions may need to be aligned. "
            "Look for triggers (crosses, switches) that transform one region."
        )
        return "\n".join(lines)


# =============================================================================
# Module F: HypothesisEngine -- Structured hypothesis generation
# =============================================================================


@dataclass
class GameHypothesis:
    """A structured hypothesis about game mechanics."""

    hypothesis: str       # "The cross at (32,21) is a trigger that rotates the pattern"
    test_action: str      # "navigate_to(32,21)"
    observe_for: str      # "Check if region (5,30)-(15,45) changed"
    priority: int         # Lower = try first
    source: str           # "shape_detection", "region_similarity", "trigger_pattern"
    tested: bool = False
    confirmed: bool = False


class HypothesisEngine:
    """Generate structured hypotheses from available intelligence.

    Synthesizes region similarities, special objects, and cross-episode
    trigger patterns into prioritized, testable hypotheses.
    """

    def generate_hypotheses(
        self,
        region_similarities: list[str],
        special_objects: list[tuple[int, int, str, int]],
        confirmed_triggers: list[TriggerHypothesis],
        first_look_text: str = "",
    ) -> list[GameHypothesis]:
        """Generate hypotheses from available intelligence.

        Args:
            region_similarities: Output of RegionComparator.find_similar_pairs()
            special_objects: (center_r, center_c, shape, color) from grid analysis
            confirmed_triggers: Known trigger hypotheses from InteractionTracker
            first_look_text: LLM first-look analysis text

        Returns:
            List of GameHypothesis sorted by priority.
        """
        hypotheses: list[GameHypothesis] = []
        priority = 0

        # PRIORITY 1: Confirmed triggers from previous episodes
        for trigger in confirmed_triggers:
            if trigger.confidence >= 2:
                priority += 1
                hypotheses.append(GameHypothesis(
                    hypothesis=(
                        f"CONFIRMED: {trigger.trigger_shape.upper()} (color {trigger.trigger_color}) "
                        f"at ({trigger.trigger_pos[0]},{trigger.trigger_pos[1]}) causes "
                        f"{trigger.effect_description}"
                    ),
                    test_action=f"Move toward ({trigger.trigger_pos[0]},{trigger.trigger_pos[1]}) using ACTION1-ACTION4",
                    observe_for=(
                        f"Grid transformation in region {trigger.effect_region}"
                        if trigger.effect_region else "Grid changes"
                    ),
                    priority=priority,
                    source="confirmed_trigger",
                    confirmed=True,
                ))

        # PRIORITY 2: Special shapes + region similarities combined
        # If we see both special shapes AND similar regions, the shape
        # is likely a trigger that transforms one region to match the other
        if region_similarities and special_objects:
            for cr, cc, shape, color in special_objects:
                if shape in ("cross", "diamond", "T-shape"):
                    priority += 1
                    sim_text = region_similarities[0] if region_similarities else ""
                    hypotheses.append(GameHypothesis(
                        hypothesis=(
                            f"The {shape.upper()} (color {color}) at ({cr},{cc}) "
                            f"may be a trigger that transforms a region. "
                            f"Nearby similarity: {sim_text}"
                        ),
                        test_action=f"Move toward ({cr},{cc}) using ACTION1-ACTION4",
                        observe_for="Watch for grid transformation after stepping on it",
                        priority=priority,
                        source="shape_plus_similarity",
                    ))

        # PRIORITY 3: Special shapes alone (likely interactive)
        for cr, cc, shape, color in special_objects:
            if shape in ("cross", "diamond", "T-shape", "L-shape", "U-shape"):
                # Skip if already covered by combined hypothesis
                already = any(
                    h.source == "shape_plus_similarity"
                    and f"({cr},{cc})" in h.test_action
                    for h in hypotheses
                )
                if already:
                    continue
                priority += 1
                hypotheses.append(GameHypothesis(
                    hypothesis=(
                        f"The {shape.upper()} (color {color}) at ({cr},{cc}) "
                        f"may be interactive. Step on it to test."
                    ),
                    test_action=f"Move toward ({cr},{cc}) using ACTION1-ACTION4",
                    observe_for="Check if grid changes or score increases",
                    priority=priority,
                    source="shape_detection",
                ))

        # PRIORITY 4: Region similarity without special shapes
        if region_similarities and not special_objects:
            priority += 1
            hypotheses.append(GameHypothesis(
                hypothesis=(
                    f"Two regions are similar: {region_similarities[0]}. "
                    f"Look for a trigger object to align them."
                ),
                test_action="Explore the area between the regions",
                observe_for="Look for cross/diamond/switch objects",
                priority=priority,
                source="region_similarity",
            ))

        # Sort by priority
        hypotheses.sort(key=lambda h: h.priority)
        return hypotheses

    @staticmethod
    def format_hypotheses(
        hypotheses: list[GameHypothesis],
        max_show: int = 3,
    ) -> str:
        """Format hypotheses for prompt injection."""
        if not hypotheses:
            return ""
        active = [h for h in hypotheses if not h.tested]
        if not active:
            return ""
        lines = ["# HYPOTHESES TO TEST"]
        for i, h in enumerate(active[:max_show], 1):
            status = "CONFIRMED" if h.confirmed else "HYPOTHESIS"
            lines.append(f"  {i}. [{status}] {h.hypothesis}")
            lines.append(f"     DO: {h.test_action}")
            lines.append(f"     WATCH: {h.observe_for}")
        lines.append(
            "Test these hypotheses IN ORDER. "
            "After each test, check what changed before moving on."
        )
        return "\n".join(lines)
