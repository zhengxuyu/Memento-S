---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer**: Color 11 bar at the bottom.
- **Button**: Centered at Y=10, X=49.

# Level 3 Dead Ends & Blocks
- At `(15,34)`, UP and RIGHT are BLOCKED.
- At `(25,34)`, RIGHT is BLOCKED.

# Current Plan
- I am at `(15,34)`. I went LEFT and UP into a huge dead end.
- I need to backtrack DOWN. I will move DOWN to `(30,34)`, then RIGHT to `(30,49)`.
- From `(30,49)`, I need to explicitly try going UP to `(10,49)` to reach the button!!
- My previous movement into `(15,34)` was a mistake when plotting a path to the button. Backtracking now.