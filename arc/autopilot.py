"""AutoPilot: Competence Without Comprehension layers for the agent.

Implements Dennett-inspired cognitive architecture layers:
- Layer 1 (Competence w/o Comprehension): AutoPilot — action mapping,
  object-seeking via BFS, no LLM calls.
- Layer 2 (Intentional Stance): BeliefState + systematic hypothesis testing.

The AutoPilot never calls the LLM. All decisions are algorithmic
(BFS, displacement tracking, object inventory).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from arc.game_intelligence import (
        GameHypothesis,
        GridNavigator,
        InteractionTracker,
        ObjectInventory,
    )
    from arc.grid_perception import GridPerception

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Hypothesis (Rathering — no vague claims)
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Hypothesis:
    """A concrete, testable prediction about game mechanics."""

    prediction: str       # "Stepping on cross at (32,21) rotates region"
    test_action: str      # "Move to (32,21)"
    expected: str         # "Grid cells in region change"
    target_pos: Optional[tuple[int, int]] = None  # extracted coordinates
    tested: bool = False
    result: str = ""      # "CONFIRMED" / "REFUTED" / "UNREACHABLE"


# ──────────────────────────────────────────────────────────────────────
# BeliefState (Intentional Stance)
# ──────────────────────────────────────────────────────────────────────

@dataclass
class BeliefState:
    """Structured beliefs: what the agent knows/suspects about the game."""

    # ACTION1->"UP" | None = untested
    action_map: dict[str, Optional[str]] = field(default_factory=lambda: {
        "ACTION1": None,
        "ACTION2": None,
        "ACTION3": None,
        "ACTION4": None,
    })
    hypotheses: list[Hypothesis] = field(default_factory=list)
    active_hypothesis_idx: int = -1
    last_prediction: str = ""  # for Pump 1: prediction vs reality
    phase: str = "mapping"     # mapping -> exploring -> hypothesis_testing -> exploiting
    failure_analysis: str = "" # Rapoport's Rules from previous retry
    confirmed_rules: list[str] = field(default_factory=list)
    # Track which mapping step we're on (0-3 for ACTION1-ACTION4)
    _mapping_step: int = 0

    def summarize(self) -> str:
        """Compact summary for LLM prompt (<200 tokens)."""
        parts: list[str] = []

        # Action mappings
        known = {k: v for k, v in self.action_map.items() if v is not None}
        unknown = [k for k, v in self.action_map.items() if v is None]
        if known:
            maps = ", ".join(f"{k}={v}" for k, v in sorted(known.items()))
            parts.append(f"Actions: {maps}")
        if unknown:
            parts.append(f"Untested: {', '.join(unknown)}")

        # Phase
        parts.append(f"Phase: {self.phase}")

        # Active hypothesis
        if self.active_hypothesis_idx >= 0 and self.active_hypothesis_idx < len(self.hypotheses):
            h = self.hypotheses[self.active_hypothesis_idx]
            if not h.tested:
                parts.append(f"Testing: {h.prediction}")

        # Confirmed rules
        if self.confirmed_rules:
            parts.append(f"Rules: {'; '.join(self.confirmed_rules[-3:])}")

        # Failure analysis (from previous retry)
        if self.failure_analysis:
            parts.append(f"Last attempt: {self.failure_analysis[:150]}")

        return " | ".join(parts)


# ──────────────────────────────────────────────────────────────────────
# AutoPilot (Competence Without Comprehension)
# ──────────────────────────────────────────────────────────────────────

_DISPLACEMENT_TO_DIR: dict[tuple[int, int], str] = {
    (-1, 0): "UP",    # negative row = up
    (1, 0): "DOWN",   # positive row = down
    (0, -1): "LEFT",  # negative col = left
    (0, 1): "RIGHT",  # positive col = right
}


class AutoPilot:
    """Algorithmic decision-making: no LLM calls.

    Handles:
    - Mapping phase (steps 0-3): test each ACTION systematically
    - Exploring phase (steps 4-7): BFS to nearest unvisited special object
    - Hypothesis testing: navigate to hypothesis targets
    """

    def __init__(
        self,
        navigator: GridNavigator,
        inventory: ObjectInventory,
        interaction_tracker: InteractionTracker,
        perception: GridPerception,
    ) -> None:
        self.navigator = navigator
        self.inventory = inventory
        self.interaction_tracker = interaction_tracker
        self.perception = perception
        self.beliefs = BeliefState()
        # BFS path being followed
        self._current_path: list[str] = []
        self._current_target: Optional[tuple[int, int]] = None

    def should_autopilot(self, step_count: int, score: int) -> bool:
        """Decide whether autopilot should handle this step."""
        phase = self.beliefs.phase

        # Mapping phase (steps 0-3): always autopilot
        if phase == "mapping":
            return True

        # Exploring phase: autopilot if we have a path or reachable target
        if phase == "exploring":
            if self._current_path:
                return True
            # Check if there are unvisited special objects to seek
            return self._has_reachable_target()

        # Hypothesis testing: autopilot if we have a path to hypothesis target
        if phase == "hypothesis_testing":
            if self._current_path:
                return True
            # Check if current hypothesis has a reachable target
            return self._has_active_hypothesis_target()

        return False

    def choose_action(self, player_pos: Optional[tuple[int, int]], grid: Optional[list[list[int]]]) -> Optional[str]:
        """Choose next action algorithmically. Returns None to hand off to LLM."""
        phase = self.beliefs.phase

        # ── Mapping phase ──
        if phase == "mapping":
            return self._mapping_action()

        # ── Following existing path ──
        if self._current_path:
            action = self._current_path.pop(0)
            return action

        # ── Exploring phase: BFS to nearest special object ──
        if phase == "exploring" and player_pos:
            return self._explore_action(player_pos)

        # ── Hypothesis testing: navigate to hypothesis target ──
        if phase == "hypothesis_testing" and player_pos:
            return self._hypothesis_action(player_pos)

        return None  # hand off to LLM

    def update_after_action(
        self,
        action: str,
        prev_pos: Optional[tuple[int, int]],
        curr_pos: Optional[tuple[int, int]],
        score_delta: int,
        grid_changed: bool,
    ) -> None:
        """Learn from action result. Update beliefs and phase transitions."""
        from arc.game_intelligence import STEP_SIZE

        # ── Learn action→direction from displacement ──
        if prev_pos and curr_pos and prev_pos != curr_pos:
            dr = curr_pos[0] - prev_pos[0]
            dc = curr_pos[1] - prev_pos[1]
            # Normalize to unit direction
            if dr != 0:
                dr = dr // abs(dr)
            if dc != 0:
                dc = dc // abs(dc)
            direction = _DISPLACEMENT_TO_DIR.get((dr, dc))
            if direction and action in self.beliefs.action_map:
                old = self.beliefs.action_map[action]
                self.beliefs.action_map[action] = direction
                if old != direction:
                    logger.info(
                        "AutoPilot: learned %s=%s (was %s)",
                        action, direction, old,
                    )
        elif prev_pos and curr_pos and prev_pos == curr_pos:
            # Action had no movement effect — might be wall or non-movement action
            if action in self.beliefs.action_map and self.beliefs.action_map[action] is None:
                self.beliefs.action_map[action] = "BLOCKED"
                logger.info("AutoPilot: %s had no effect (wall/blocked)", action)

        # ── Phase transitions ──
        if self.beliefs.phase == "mapping":
            self.beliefs._mapping_step += 1
            # After testing all 4 directional actions, transition
            if self.beliefs._mapping_step >= 4:
                self._transition_to_exploring()

        # ── Score increase: reset exploration and advance ──
        if score_delta > 0:
            self._current_path = []
            self._current_target = None
            logger.info("AutoPilot: score increased by %d, clearing path", score_delta)

        # ── Path following: check if we reached target ──
        if self._current_target and curr_pos:
            qr = (curr_pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (curr_pos[1] // STEP_SIZE) * STEP_SIZE
            tr = (self._current_target[0] // STEP_SIZE) * STEP_SIZE
            tc = (self._current_target[1] // STEP_SIZE) * STEP_SIZE
            if (qr, qc) == (tr, tc):
                logger.info(
                    "AutoPilot: reached target (%d,%d)",
                    self._current_target[0], self._current_target[1],
                )
                self._current_path = []
                self._current_target = None

        # ── Wall hit while path-following: abandon path ──
        if not grid_changed and self._current_path:
            logger.info("AutoPilot: wall hit, abandoning path")
            self._current_path = []
            self._current_target = None

    def import_hypotheses(self, engine_hypotheses: list[GameHypothesis]) -> None:
        """Convert HypothesisEngine output to validated Hypothesis objects.

        Rathering: reject hypotheses without coordinates or observable expected outcome.
        """
        self.beliefs.hypotheses = []
        for h in engine_hypotheses:
            # Extract coordinates from test_action like "Move toward (32,21) ..."
            m = re.search(r"\((\d+),\s*(\d+)\)", h.test_action)
            if not m:
                continue  # Reject: no concrete target position
            target_pos = (int(m.group(1)), int(m.group(2)))

            self.beliefs.hypotheses.append(Hypothesis(
                prediction=h.hypothesis,
                test_action=h.test_action,
                expected=h.observe_for,
                target_pos=target_pos,
            ))

        if self.beliefs.hypotheses:
            self.beliefs.active_hypothesis_idx = 0
            logger.info(
                "AutoPilot: imported %d hypotheses",
                len(self.beliefs.hypotheses),
            )

    def reset_episode(self, keep_beliefs: bool = False) -> None:
        """Clear per-episode state.

        If keep_beliefs: preserve action_map, confirmed_rules, failure_analysis.
        """
        self._current_path = []
        self._current_target = None

        if keep_beliefs:
            # Preserve cross-episode knowledge
            saved_map = dict(self.beliefs.action_map)
            saved_rules = list(self.beliefs.confirmed_rules)
            saved_failure = self.beliefs.failure_analysis
            self.beliefs = BeliefState()
            self.beliefs.action_map = saved_map
            self.beliefs.confirmed_rules = saved_rules
            self.beliefs.failure_analysis = saved_failure
            # Skip mapping if we already know the actions
            known_count = sum(
                1 for v in saved_map.values()
                if v is not None and v != "BLOCKED"
            )
            if known_count >= 2:
                self.beliefs.phase = "exploring"
                self.beliefs._mapping_step = 4
        else:
            self.beliefs = BeliefState()

    # ──────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────

    def _mapping_action(self) -> Optional[str]:
        """Return next untested ACTION for mapping phase."""
        actions = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
        step = self.beliefs._mapping_step
        if step < len(actions):
            action = actions[step]
            # Set prediction for Pump 1
            self.beliefs.last_prediction = (
                f"Testing {action} — expecting directional movement"
            )
            logger.info("AutoPilot: mapping step %d -> %s", step, action)
            return action
        # All tested, transition
        self._transition_to_exploring()
        return None

    def _transition_to_exploring(self) -> None:
        """Transition from mapping to exploring phase."""
        self.beliefs.phase = "exploring"
        logger.info(
            "AutoPilot: mapping complete, action_map=%s, transitioning to exploring",
            self.beliefs.action_map,
        )

    def _explore_action(self, player_pos: tuple[int, int]) -> Optional[str]:
        """BFS to nearest unvisited special object."""
        from arc.game_intelligence import ObjectStatus

        # Find nearest active (unvisited) object
        active_items = [
            item for item in self.inventory._items
            if item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
        ]
        if not active_items:
            # No objects to explore — hand off to LLM
            return None

        active_items.sort(key=lambda i: i.distance_actions)
        target = active_items[0]
        target_pos = target.position

        # Compute BFS path
        self.navigator.update_action_mappings(self.perception._action_effects)
        path = self.navigator.navigate_to(
            target_pos[0], target_pos[1],
            player_pos[0], player_pos[1],
            max_steps=15,
        )
        if path:
            self._current_path = path[1:]  # save rest for next steps
            self._current_target = target_pos
            self.beliefs.last_prediction = (
                f"Moving toward {target.shape or 'object'} "
                f"color {target.color} at ({target_pos[0]},{target_pos[1]})"
            )
            logger.info(
                "AutoPilot: exploring -> %s at (%d,%d), path=%s",
                target.shape, target_pos[0], target_pos[1], path,
            )
            return path[0]

        return None  # no path, hand off to LLM

    def _hypothesis_action(self, player_pos: tuple[int, int]) -> Optional[str]:
        """Navigate to the active hypothesis target."""
        hyps = self.beliefs.hypotheses
        idx = self.beliefs.active_hypothesis_idx

        # Advance past tested hypotheses
        while idx < len(hyps) and hyps[idx].tested:
            idx += 1
        self.beliefs.active_hypothesis_idx = idx

        if idx >= len(hyps):
            # All hypotheses tested, transition to exploring
            self.beliefs.phase = "exploring"
            logger.info("AutoPilot: all hypotheses tested, back to exploring")
            return None

        h = hyps[idx]
        if h.target_pos is None:
            h.tested = True
            h.result = "UNREACHABLE"
            return self._hypothesis_action(player_pos)

        # Compute BFS path to hypothesis target
        self.navigator.update_action_mappings(self.perception._action_effects)
        path = self.navigator.navigate_to(
            h.target_pos[0], h.target_pos[1],
            player_pos[0], player_pos[1],
            max_steps=15,
        )
        if path:
            self._current_path = path[1:]
            self._current_target = h.target_pos
            self.beliefs.last_prediction = f"Hypothesis: {h.prediction}"
            logger.info(
                "AutoPilot: hypothesis test -> (%d,%d), path=%s",
                h.target_pos[0], h.target_pos[1], path,
            )
            return path[0]

        # Unreachable
        h.tested = True
        h.result = "UNREACHABLE"
        logger.info(
            "AutoPilot: hypothesis target (%d,%d) unreachable",
            h.target_pos[0], h.target_pos[1],
        )
        return self._hypothesis_action(player_pos)

    def _has_reachable_target(self) -> bool:
        """Check if there are any unvisited objects to explore."""
        from arc.game_intelligence import ObjectStatus
        return any(
            item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
            for item in self.inventory._items
        )

    def _has_active_hypothesis_target(self) -> bool:
        """Check if there's an untested hypothesis with a target."""
        hyps = self.beliefs.hypotheses
        idx = self.beliefs.active_hypothesis_idx
        while idx < len(hyps):
            if not hyps[idx].tested and hyps[idx].target_pos is not None:
                return True
            idx += 1
        return False
