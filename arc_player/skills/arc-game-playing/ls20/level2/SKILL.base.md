---
name: "Button-Driven Puzzle"
description: "Navigate a 5x5 grid puzzle with buttons that transform remote areas. Discover how scoring works through pattern observation."
---

# Controls
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5)
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Actions 5 and 6 do nothing.

# Game-Wide Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is strictly in 5-cell increments.
- **Timer / Action Limit**: The episode ends after exactly 100 actions.
- **Wasting Actions**: Bumping into obstacles does not move the player but still consumes 1 action.
- **Grid Alignment**: Everything aligns with 5x5 movement grid.

# CRITICAL: Discover the Scoring Mechanic
**WARNING**: The scoring mechanic on this level DIFFERS from level 1. Do NOT assume "walking onto a goal" scores.

## Discovery Protocol
1. **Map the grid**: Identify buttons (cross shapes), target patterns (small colored shapes), and any large colored regions.
2. **Press a button**: Step on it and check the observation for `🌍 WORLD CHANGED` and `📐 PATTERN ANALYSIS`.
3. **Read the auto-analysis**: The system automatically:
   - Extracts the logical pattern (grouping 2x2 sub-blocks into NxN logical cells)
   - Compares it to all similar-sized patterns elsewhere on the grid
   - Shows MATCH or NO MATCH
4. **Cycle the button**: Step off and on again. Does the pattern cycle? How many states?
5. **Find the matching state**: Keep cycling until the analysis shows MATCH with a target pattern.

## Key Insight: Pattern Matching = Scoring
- Buttons may **transform a remote area** rather than just opening gates.
- The remote area's pattern must **match a target pattern** elsewhere on the grid.
- When patterns match, scoring may happen **automatically** — no need to walk to a different location.
- The button may cycle through N states. Count them and find which state matches the target.

## Efficiency Rules
- Do NOT wander after pressing a button. Stay and cycle it systematically.
- Count states: press→observe→press→observe until the pattern repeats.
- When you find the matching state, STOP pressing. Check if score changed.
- Only navigate away once you understand the full mechanism.

## What NOT to Assume
- Do NOT assume buttons just "open gates".
- Do NOT assume you need to walk to a physical goal to score.
- Do NOT assume there's a "bridge" or "door" you need to pass through.
- The c0 cells that appear/disappear may be side effects, not the main mechanic.
