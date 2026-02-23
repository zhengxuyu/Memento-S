"""Enhanced Self-Evolving Skills for ARC-AGI-3.

Adapted from Memento-S cli/workflow_runner.py:optimize_skill_with_creator
and core/skill_engine/create_on_miss.py.

Key differences from the naive version:
1. Detects SPECIFIC failure patterns (not just consecutive GAME_OVER count).
2. Generates TARGETED patches based on failure type.
3. Applies patches IMMEDIATELY (between retries, not next session).
4. Supports creating new game-specific skill sections.

Failure patterns detected:
- LOOP: Repetitive action cycles
- STUCK: No score change for many steps
- WALL_TRAP: Repeated no-effect actions (boxed in)
- ENERGY_DEATH: Resource depletion before goal
- WRONG_ORDER: Reached goal but blocked (prerequisites missing)
- BLIND_EXPLORE: No action mappings discovered after many steps
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from arc.config import (
    ARC_AGI_MODEL,
    EVOLVE_THRESHOLD,
    KNOWLEDGE_HEADERS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from arc.episode_buffer import EpisodeBuffer, StepRecord
from arc.tools import handle_game_notes_update

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Failure pattern classification
# -------------------------------------------------------------------------

class FailureType(Enum):
    """Classified failure pattern."""
    LOOP = "loop"
    STUCK = "stuck"
    WALL_TRAP = "wall_trap"
    ENERGY_DEATH = "energy_death"
    WRONG_ORDER = "wrong_order"
    BLIND_EXPLORE = "blind_explore"
    UNKNOWN = "unknown"


@dataclass
class FailureAnalysis:
    """Result of analyzing an episode's failure."""
    failure_type: FailureType
    confidence: float  # 0-1
    details: str
    suggested_section: str  # Which SKILL.md section to evolve


def classify_failure(
    steps: list[StepRecord],
    *,
    had_action_mappings: bool = False,
    loop_detected: bool = False,
    steps_since_score: int = 0,
) -> FailureAnalysis:
    """Classify the failure pattern from an episode's steps.

    Adapted from Memento-S _is_likely_format_error / _is_skill_execution_error
    pattern matching, but applied to game failure patterns.
    """
    if not steps:
        return FailureAnalysis(
            FailureType.UNKNOWN, 0.0, "no steps", "tips",
        )

    total = len(steps)
    no_effect_count = sum(1 for s in steps if "no_change" in s.frame_diff)
    no_effect_ratio = no_effect_count / max(total, 1)
    score_changes = sum(1 for s in steps if s.score_after > s.score_before)

    # LOOP: repetitive cycles detected
    if loop_detected:
        # Find the cycle in last N actions
        actions = [s.action for s in steps[-30:]]
        cycle_str = _detect_cycle_str(actions)
        return FailureAnalysis(
            FailureType.LOOP, 0.9,
            f"Repetitive action cycle: {cycle_str}",
            "tips",
        )

    # BLIND_EXPLORE: no action mappings after many steps
    if not had_action_mappings and total > 15:
        return FailureAnalysis(
            FailureType.BLIND_EXPLORE, 0.8,
            f"No action mappings discovered after {total} steps",
            "action_mappings",
        )

    # WALL_TRAP: very high no-effect ratio (boxed in)
    if no_effect_ratio > 0.6 and total > 10:
        blocked_actions = set()
        for s in steps[-15:]:
            if "no_change" in s.frame_diff:
                blocked_actions.add(s.action)
        return FailureAnalysis(
            FailureType.WALL_TRAP, 0.85,
            f"{no_effect_ratio:.0%} actions had no effect. "
            f"Blocked actions: {sorted(blocked_actions)}",
            "tips",
        )

    # ENERGY_DEATH: score was increasing then sudden GAME_OVER
    if score_changes > 0 and steps[-1].state_text == "GAME_OVER":
        # Check if there was progress before death
        max_score = max(s.score_after for s in steps)
        if max_score > 0:
            return FailureAnalysis(
                FailureType.ENERGY_DEATH, 0.7,
                f"Made progress (score={max_score}) but died. "
                f"Likely resource depletion or hazard.",
                "game_rules",
            )

    # WRONG_ORDER: reached high areas but got stuck
    if steps_since_score > 20 and score_changes > 0:
        return FailureAnalysis(
            FailureType.WRONG_ORDER, 0.6,
            f"Score changed {score_changes} times but then stuck "
            f"for {steps_since_score} steps. May need different order.",
            "level_strategies",
        )

    # STUCK: no progress for long time
    if steps_since_score > 15 or (total > 20 and score_changes == 0):
        return FailureAnalysis(
            FailureType.STUCK, 0.7,
            f"No score change for {max(steps_since_score, total)} steps. "
            f"Strategy is not working.",
            "level_strategies",
        )

    return FailureAnalysis(
        FailureType.UNKNOWN, 0.3,
        f"Unclassified failure: {total} steps, {score_changes} score changes",
        "tips",
    )


def _detect_cycle_str(actions: list[str]) -> str:
    """Find the shortest repeating cycle in recent actions."""
    n = len(actions)
    for length in range(2, min(9, n // 2 + 1)):
        pattern = actions[-length:]
        reps = 1
        pos = n - length
        while pos >= length:
            if actions[pos - length:pos] == pattern:
                reps += 1
                pos -= length
            else:
                break
        if reps >= 2:
            return f"{','.join(pattern)} x{reps}"
    return ",".join(actions[-5:])


# -------------------------------------------------------------------------
# Evolution prompts (per failure type)
# -------------------------------------------------------------------------

_EVOLUTION_PROMPTS: dict[FailureType, str] = {
    FailureType.LOOP: (
        "The agent is stuck in a REPETITIVE LOOP. Analyze the cycle and suggest:\n"
        "1. What causes the loop (wall bounce? back-and-forth?)\n"
        "2. How to BREAK the loop (try different direction? interact?)\n"
        "3. A specific tip to add to prevent this pattern."
    ),
    FailureType.STUCK: (
        "The agent is STUCK with no score progress. Suggest:\n"
        "1. Alternative exploration strategies\n"
        "2. What the agent might be missing (hidden objects? different path?)\n"
        "3. Level strategy updates."
    ),
    FailureType.WALL_TRAP: (
        "The agent keeps hitting WALLS (most actions have no effect). Suggest:\n"
        "1. How to navigate out (try ACTION5/ACTION6? search for openings?)\n"
        "2. Wall avoidance tips\n"
        "3. Whether the agent should reset and try a different starting direction."
    ),
    FailureType.ENERGY_DEATH: (
        "The agent DIED after making progress (likely resource depletion). Suggest:\n"
        "1. What resource rules were observed (energy bar? health?)\n"
        "2. How to manage resources (collect refills? shorter paths?)\n"
        "3. Game rules about resource management."
    ),
    FailureType.WRONG_ORDER: (
        "The agent made progress but got STUCK later. Suggest:\n"
        "1. What prerequisites might be needed in different order\n"
        "2. Whether objects need to be collected in specific sequence\n"
        "3. Level strategy adjustments."
    ),
    FailureType.BLIND_EXPLORE: (
        "The agent failed to DISCOVER action mappings. Suggest:\n"
        "1. Systematic action testing strategy (try each ACTION1-6)\n"
        "2. How to identify which actions cause movement\n"
        "3. Action mapping tips."
    ),
    FailureType.UNKNOWN: (
        "The agent failed for unclear reasons. Suggest:\n"
        "1. General strategy improvements\n"
        "2. What patterns to look for\n"
        "3. Any tips that might help."
    ),
}


# -------------------------------------------------------------------------
# SkillEvolution class
# -------------------------------------------------------------------------

class SkillEvolution:
    """Enhanced self-evolving skills with failure pattern detection.

    Adapted from Memento-S optimize_skill_with_creator pattern:
    1. Detect failure type (like _is_likely_format_error)
    2. Build targeted repair prompt
    3. Call LLM to generate patch
    4. Apply patch to SKILL.md
    5. Validate and retry
    """

    def __init__(
        self,
        game_id: str,
        skill_path: Path,
        threshold: int = EVOLVE_THRESHOLD,
        max_optimize_attempts: int = 2,
    ):
        self.game_id = game_id
        self.skill_path = skill_path
        self.threshold = threshold
        self.max_optimize_attempts = max_optimize_attempts
        self._consecutive_failures: int = 0
        self._failure_history: list[FailureAnalysis] = []

    def record_outcome(self, success: bool) -> None:
        """Record a game outcome."""
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

    def should_evolve(self) -> bool:
        """Check if evolution should be triggered."""
        return self._consecutive_failures >= self.threshold

    def analyze_and_evolve(
        self,
        episode_buffer: EpisodeBuffer,
        current_steps: list[StepRecord],
        *,
        had_action_mappings: bool = False,
        loop_detected: bool = False,
        steps_since_score: int = 0,
    ) -> bool:
        """Analyze the latest failure and immediately evolve the skill.

        This is called BETWEEN retries (not after all retries exhausted),
        so the fix takes effect on the very next attempt.

        Returns True if evolution was performed.
        """
        # Classify the failure
        analysis = classify_failure(
            current_steps,
            had_action_mappings=had_action_mappings,
            loop_detected=loop_detected,
            steps_since_score=steps_since_score,
        )
        self._failure_history.append(analysis)

        logger.info(
            "Failure classified: %s (confidence=%.2f) — %s",
            analysis.failure_type.value, analysis.confidence, analysis.details,
        )

        # Only evolve if confidence is high enough
        if analysis.confidence < 0.5:
            return False

        # Check if we've already tried evolving for this failure type recently
        recent_types = [
            fa.failure_type for fa in self._failure_history[-3:]
        ]
        same_type_count = sum(
            1 for t in recent_types if t == analysis.failure_type
        )
        if same_type_count > self.max_optimize_attempts:
            logger.info(
                "Already tried evolving for %s %d times, skipping",
                analysis.failure_type.value, same_type_count,
            )
            return False

        # Collect context from episode buffer
        failed_episodes = [
            ep for ep in episode_buffer.episodes
            if ep.game_id == self.game_id and not ep.success
        ]
        recent_summaries = "\n".join(
            ep.summary(max_steps=6) for ep in failed_episodes[-3:]
        )

        # Build evolution prompt
        prompt = self._build_prompt(analysis, recent_summaries, current_steps)

        # Call LLM for patch
        for attempt in range(1, self.max_optimize_attempts + 1):
            logger.info(
                "Evolution attempt %d/%d for %s",
                attempt, self.max_optimize_attempts, analysis.failure_type.value,
            )
            patch = self._call_llm(prompt)
            if patch:
                applied = self._apply_patch(patch, analysis)
                if applied:
                    logger.info(
                        "Skill evolved for %s — patch applied to %s",
                        analysis.failure_type.value, analysis.suggested_section,
                    )
                    return True
            logger.warning("Evolution attempt %d failed", attempt)

        return False

    def evolve(self, episode_buffer: EpisodeBuffer) -> bool:
        """Legacy interface: evolve after threshold failures."""
        if not self.should_evolve():
            return False

        # Use the last failure's steps (if available)
        failed = [
            ep for ep in episode_buffer.episodes
            if ep.game_id == self.game_id and not ep.success
        ]
        if not failed:
            return False

        last_ep = failed[-1]
        return self.analyze_and_evolve(
            episode_buffer,
            last_ep.steps,
            had_action_mappings=True,
            loop_detected=False,
            steps_since_score=last_ep.total_actions,
        )

    def _build_prompt(
        self,
        analysis: FailureAnalysis,
        episode_summaries: str,
        current_steps: list[StepRecord],
    ) -> str:
        """Build a targeted evolution prompt based on failure type."""
        # Read current SKILL.md
        current_skill = ""
        if self.skill_path.exists():
            try:
                current_skill = self.skill_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Get failure-specific instructions
        specific_instructions = _EVOLUTION_PROMPTS.get(
            analysis.failure_type,
            _EVOLUTION_PROMPTS[FailureType.UNKNOWN],
        )

        # Recent action trail
        recent_actions = ""
        if current_steps:
            trail = []
            for s in current_steps[-20:]:
                marker = ""
                if s.score_after > s.score_before:
                    marker = " [SCORE+]"
                elif "no_change" in s.frame_diff:
                    marker = " [NO EFFECT]"
                trail.append(f"  {s.action}{marker}")
            recent_actions = "\n".join(trail)

        return f"""You are analyzing a FAILED attempt at an ARC-AGI-3 grid game.

## Failure Classification
Type: {analysis.failure_type.value}
Details: {analysis.details}

## Recent Actions Trail
{recent_actions or '(none)'}

## Past Episode Summaries
{episode_summaries[:2000] or '(none)'}

## Current SKILL.md Knowledge Sections
{self._extract_knowledge_sections(current_skill)}

## Your Task
{specific_instructions}

## Output Format
Respond with JSON containing the sections to update:
```json
{{
  "section": "{analysis.suggested_section}",
  "content": "your updated content here (markdown)",
  "replace": false,
  "reasoning": "why this change should help"
}}
```

Rules:
- Only include CONFIRMED observations from the failure data.
- Be specific and actionable (not generic advice).
- Content should be concise (2-5 bullet points).
- Set replace=true only if the existing content is wrong, false to append."""

    def _extract_knowledge_sections(self, skill_text: str) -> str:
        """Extract just the Discovered Knowledge sections."""
        marker = "## Discovered Knowledge"
        idx = skill_text.find(marker)
        if idx >= 0:
            return skill_text[idx:idx + 2000]
        # Try individual sections
        parts = []
        for section, header in KNOWLEDGE_HEADERS.items():
            idx = skill_text.find(header)
            if idx >= 0:
                end = len(skill_text)
                for h in KNOWLEDGE_HEADERS.values():
                    pos = skill_text.find(h, idx + len(header))
                    if pos > 0 and pos < end:
                        end = pos
                parts.append(skill_text[idx:end].strip())
        return "\n\n".join(parts) if parts else "(no knowledge sections found)"

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM for evolution patch."""
        # Try Memento-S core.llm first
        try:
            from core.llm import openrouter_messages
            return openrouter_messages(
                system="You are an ARC-AGI-3 game strategy analyst. "
                       "Analyze failures and generate precise SKILL.md patches.",
                messages=[{"role": "user", "content": prompt}],
            )
        except ImportError:
            pass

        # Fallback: direct OpenAI SDK via OpenRouter
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
                base_url=OPENROUTER_BASE_URL,
            )
            create_kwargs: dict[str, Any] = {
                "model": ARC_AGI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an ARC-AGI-3 game strategy analyst. "
                            "Analyze failures and generate precise SKILL.md patches."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1500,
            }
            provider = os.environ.get("OPENROUTER_PROVIDER", "").strip()
            if provider:
                create_kwargs["extra_body"] = {"provider": {"order": [provider]}}
            response = client.chat.completions.create(**create_kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("Evolution LLM call failed: %s", e)
            return None

    def _apply_patch(self, response: str, analysis: FailureAnalysis) -> bool:
        """Parse LLM response and apply patch to SKILL.md."""
        # Try to extract JSON from response
        parsed = self._parse_json_from_response(response)
        if not parsed:
            # Fallback: try to use the whole response as content
            logger.info("No JSON in response, using as raw content")
            parsed = {
                "section": analysis.suggested_section,
                "content": response.strip(),
                "replace": "false",
            }

        section = parsed.get("section", analysis.suggested_section)
        content = parsed.get("content", "").strip()
        replace = str(parsed.get("replace", "false"))

        if not content:
            return False

        if section not in KNOWLEDGE_HEADERS:
            section = analysis.suggested_section

        args_json = json.dumps({
            "section": section,
            "content": content,
            "replace": replace,
        })
        result = handle_game_notes_update(
            args_json, self.skill_path,
            score=None,  # evolution happens after failure, score=0 at this point
            trigger="skill_evolution",
        )
        logger.info("Evolution patch [%s]: %s", section, result[:100])
        return "Updated" in result or "Error" not in result

    @staticmethod
    def _parse_json_from_response(text: str) -> Optional[dict[str, Any]]:
        """Extract JSON object from LLM response (may be in code block)."""
        # Try full text as JSON
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to find JSON in code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object
        match = re.search(r"\{[^{}]*\"section\"[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None
