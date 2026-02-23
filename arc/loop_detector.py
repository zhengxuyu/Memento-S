"""Loop and stuck detection for the ReactBufferAgent."""
from __future__ import annotations

from dataclasses import dataclass, field

from arc.episode_buffer import StepRecord


@dataclass
class LoopDetection:
    """Result of loop/stuck analysis on the current action history."""

    is_looping: bool = False
    cycle_actions: list[str] = field(default_factory=list)
    cycle_length: int = 0
    cycle_repetitions: int = 0
    steps_since_score_change: int = 0
    is_stuck: bool = False
    no_effect_actions: dict[str, int] = field(default_factory=dict)
    recent_action_summary: str = ""


class LoopDetector:
    """Detects repetitive action cycles and score staleness."""

    STUCK_THRESHOLD: int = 8
    HISTORY_WINDOW: int = 15
    MIN_CYCLE_LENGTH: int = 2
    MAX_CYCLE_LENGTH: int = 8
    MIN_REPETITIONS: int = 2
    SEVERE_REPETITIONS: int = 3

    def reset(self) -> None:
        pass  # Stateless

    def analyze(self, steps: list[StepRecord]) -> LoopDetection:
        if not steps:
            return LoopDetection()

        actions = [s.action for s in steps]
        cycle_actions, cycle_length, cycle_reps = self._detect_cycle(actions)
        steps_since = self._compute_steps_since_score_change(steps)
        no_effect = self._compute_no_effect_streaks(steps)

        window = actions[-self.HISTORY_WINDOW:]
        summary_parts: list[str] = []
        for i, act in enumerate(window):
            idx = len(actions) - len(window) + i
            step = steps[idx]
            markers = ""
            if step.score_after > step.score_before:
                markers = " [SCORE+]"
            elif "no_change" in step.frame_diff:
                markers = " [NO EFFECT]"
            summary_parts.append(f"Step {idx}: {act}{markers}")

        return LoopDetection(
            is_looping=cycle_reps >= self.MIN_REPETITIONS,
            cycle_actions=cycle_actions,
            cycle_length=cycle_length,
            cycle_repetitions=cycle_reps,
            steps_since_score_change=steps_since,
            is_stuck=steps_since >= self.STUCK_THRESHOLD,
            no_effect_actions=no_effect,
            recent_action_summary="\n".join(summary_parts),
        )

    def _detect_cycle(self, actions: list[str]) -> tuple[list[str], int, int]:
        n = len(actions)
        best: tuple[list[str], int, int] = ([], 0, 0)
        for length in range(self.MAX_CYCLE_LENGTH, self.MIN_CYCLE_LENGTH - 1, -1):
            if length > n:
                continue
            pattern = actions[-length:]
            reps = 1
            pos = n - length
            while pos >= length:
                segment = actions[pos - length:pos]
                if segment == pattern:
                    reps += 1
                    pos -= length
                else:
                    break
            if reps >= self.MIN_REPETITIONS and reps > best[2]:
                best = (pattern, length, reps)
        return best

    def _compute_steps_since_score_change(self, steps: list[StepRecord]) -> int:
        for i in range(len(steps) - 1, -1, -1):
            if steps[i].score_after != steps[i].score_before:
                return len(steps) - 1 - i
        return len(steps)

    def _compute_no_effect_streaks(self, steps: list[StepRecord]) -> dict[str, int]:
        result: dict[str, int] = {}
        seen_effective: set[str] = set()
        for step in reversed(steps[-self.HISTORY_WINDOW:]):
            if step.action in seen_effective:
                continue
            if "no_change" in step.frame_diff:
                result[step.action] = result.get(step.action, 0) + 1
            else:
                seen_effective.add(step.action)
        return result
