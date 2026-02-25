---
name: "Button & Gate Alignment"
description: "Navigate a 5x5 block to step on switches to open gates, then precisely align over a 3x3 goal before time runs out."
---

# How To Win (step-by-step)
1. Locate the switch mechanism (small cluster of colors 0 and 1).
2. Move the 5x5 player block to overlap the switch, triggering the gates to open.
3. Confirm that the barricades (color 5 impassable terrain) blocking the goal have converted into passable space (color 0 or 3).
4. Navigate to the 3x3 goal symbol (made of color 9).
5. Perfectly align the center 3x3 area of your 5x5 player block exactly over the 3x3 goal footprint. Your block's outer border will extend 1 cell past the goal on all sides.

# Controls
- Action 1: UP (Y decreases by 5)
- Action 2: DOWN (Y increases by 5)
- Action 3: LEFT (X decreases by 5)
- Action 4: RIGHT (X increases by 5)

# Key Facts
- **Player Structure**: A 5x5 block (top two rows are color 12, bottom three are color 9). Moves strictly in 5-cell intervals.
- **Timer Constraint**: Watch the color 11 blocks at the bottom limit. Two blocks vanish every move. Avoid all unnecessary steps.
- **Gates**: Color 5 is impassable terrain until triggered.
- **Goal Completion**: Requires pinpoint alignment of the player block centers, not just touching the goal.