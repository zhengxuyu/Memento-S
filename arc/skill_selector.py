"""Situation-based skill selection for the ARC agent.

Detects the agent's cognitive situation programmatically, then maps it
to the most relevant Dennett thinking tools. Zero API cost.
"""
from __future__ import annotations

import logging
from typing import Any

from arc.skills_loader import load_skill_summaries

logger = logging.getLogger(__name__)

# ── Situation → Skill mapping ────────────────────────────────────────
# Each situation maps to a list of skill directory names (max 5 per situation).
# Skills are ordered by relevance (most relevant first).

SITUATION_SKILLS: dict[str, list[str]] = {
    # First steps of an episode — discover game mechanics
    "exploring": [
        "intentional-stance",       # treat game as having "intentions"
        "frogs-eye",                # perception is interpretation
        "making-mistakes",          # errors are learning
        "folk-psychology",          # common-sense reasoning
        "algorithms",              # think systematically
    ],
    # Actions produce no grid change — hitting walls or no-ops
    "stuck_no_change": [
        "jootsing",                 # break out of assumptions
        "occams-razor",             # simplest explanation
        "reductio-ad-absurdum",     # current premise is wrong
        "two-black-boxes",          # judge by behavior
        "tuned-deck",              # maybe being fooled
    ],
    # Grid changes but score stays 0 — doing things but not scoring
    "stuck_no_score": [
        "competence-without-comprehension",  # doing without understanding
        "free-floating-rationales",          # hidden pattern
        "library-of-babel",                  # need better search heuristics
        "cycles",                            # look for feedback loops
        "cranes-and-skyhooks",              # seek real mechanisms
    ],
    # Same action repeated 3+ times — behavioral loop
    "repeating": [
        "sphexishness",            # rigid loop detection
        "cycles",                  # understand the loop
        "conways-game-of-life",    # small changes → emergent effects
        "jootsing",                # break out
    ],
    # Starting a new episode after failure
    "retrying": [
        "rapoports-rules",         # steel-man previous approach
        "making-mistakes",          # extract lessons
        "three-species-of-goulding",# avoid cognitive fallacies
        "sphexishness",            # don't repeat same failing loop
        "skill_acquistion",        # systematic learning framework
    ],
    # Score just increased — something worked!
    "scored": [
        "competence-without-comprehension",  # understand WHY
        "free-floating-rationales",          # extract the rule
        "locusts-and-primes",               # mechanism may differ from assumption
        "automating-the-elevator",          # codify what works
    ],
    # Running low on action budget
    "late_game": [
        "occams-razor",            # go with simplest hypothesis
        "rock-paper-scissors",     # strategic choice under uncertainty
        "sturgeons-law",           # focus on what's likely to work
    ],
    # Long-term stuck — need creative breakthrough
    "creative_need": [
        "jootsing",                # jump out of the system
        "universal-acid",          # question ALL assumptions
        "library-of-babel",        # radical exploration
        "boom-crutch",             # maybe your mental model is wrong
        "deepity",                 # is your hypothesis profound or trivial?
    ],
}

# ── Skill summary cache ──────────────────────────────────────────────
_skill_cache: dict[str, tuple[str, str]] | None = None  # dir_name -> (name, desc)


def _load_cache() -> dict[str, tuple[str, str]]:
    """Load and cache all skill summaries (name, description) keyed by dir name."""
    global _skill_cache
    if _skill_cache is not None:
        return _skill_cache
    _skill_cache = {}
    try:
        for dir_name, name, desc in load_skill_summaries():
            _skill_cache[dir_name] = (name, desc)
        logger.info("Skill selector: cached %d skill summaries", len(_skill_cache))
    except Exception as e:
        logger.warning("Skill selector: failed to load summaries: %s", e)
    return _skill_cache


# ── Situation detection ──────────────────────────────────────────────

def detect_situations(
    current_steps: list[dict[str, Any]],
    retry_count: int = 0,
    max_actions: int = 21,
) -> list[str]:
    """Detect the agent's current cognitive situations from game state.

    Returns a list of situation tags ordered by specificity (most specific first).
    More specific situations take priority for skill selection.
    """
    situations: list[str] = []
    n = len(current_steps)

    # ── Specific situations first (highest priority) ──

    if n >= 3:
        recent = current_steps[-5:] if n >= 5 else current_steps

        # Scored: score just increased
        if n >= 1:
            last_step = current_steps[-1]
            prev_score = current_steps[-2].get("score", 0) if n >= 2 else 0
            curr_score = last_step.get("score", 0)
            if curr_score > prev_score:
                situations.append("scored")

        # Repeating: same action 3+ times in a row
        last_actions = [s.get("action", "") for s in current_steps[-3:]]
        if len(set(last_actions)) == 1 and last_actions[0]:
            situations.append("repeating")

        # Stuck (no change): last 3+ actions produced no grid change
        no_change_streak = 0
        for step in reversed(recent):
            if "no_change" in step.get("effect", ""):
                no_change_streak += 1
            else:
                break
        if no_change_streak >= 3:
            situations.append("stuck_no_change")

        # Creative need: stuck for very long (most desperate)
        if n >= 12 and all(s.get("score", 0) == 0 for s in current_steps):
            situations.append("creative_need")
        # Stuck (no score): many steps with score still 0
        elif n >= 8 and all(s.get("score", 0) == 0 for s in current_steps):
            situations.append("stuck_no_score")

    # ── General situations (lower priority) ──

    # Retrying: not the first episode
    if retry_count > 0 and n < 3:
        situations.append("retrying")

    # Late game: approaching action budget
    if n > max_actions * 0.7:
        situations.append("late_game")

    # Exploring: first few steps (lowest priority — fallback)
    if n < 5:
        situations.append("exploring")

    # Default fallback
    if not situations:
        situations.append("exploring")

    return situations


# ── Main API ─────────────────────────────────────────────────────────

def select_skills(
    current_steps: list[dict[str, Any]],
    retry_count: int = 0,
    max_actions: int = 21,
    max_skills: int = 5,
) -> str:
    """Select relevant skills based on current situation.

    Returns a formatted string of skill summaries to inject into the prompt.
    Returns empty string if no skills matched.
    """
    cache = _load_cache()
    if not cache:
        return ""

    situations = detect_situations(current_steps, retry_count, max_actions)
    logger.info("Skill selector: situations=%s", situations)

    # Collect unique skills from all detected situations, preserving order
    seen: set[str] = set()
    selected: list[tuple[str, str, str]] = []  # (dir_name, name, desc)

    for sit in situations:
        for dir_name in SITUATION_SKILLS.get(sit, []):
            if dir_name not in seen and dir_name in cache:
                seen.add(dir_name)
                name, desc = cache[dir_name]
                selected.append((dir_name, name, desc))
            if len(selected) >= max_skills:
                break
        if len(selected) >= max_skills:
            break

    if not selected:
        return ""

    lines = [f"# Thinking Tools (for current situation: {', '.join(situations)})"]
    for _, name, desc in selected:
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)
