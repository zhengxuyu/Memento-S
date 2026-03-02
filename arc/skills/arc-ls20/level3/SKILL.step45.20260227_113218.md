---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Level 3 has multiple."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action. (1: UP, 2: DOWN, 3: LEFT, 4: RIGHT)
- **Timer / Action Limit**: Color 11 bar at the bottom.
- **Time Extenders**: 3x3 U-shapes of color 11 that grant extra time.

# Level 3 Route Info
- Start: `(45,9)`
- **Collect Time Extender #1**: `... -> (5,29) -> RIGHT -> (5,34)` -> Dead end. Backtrack LEFT to `(5,29)`.
- Move DOWN -> `(10,29)`. At `(10,29)`, RIGHT is blocked.
- Move DOWN to `(15,29)`, RIGHT to `(15,34)`, DOWN to `(25,34)`.
- At `(25,34)`, RIGHT paths to X=39,44,49 are blocked from going UP.
- Move DOWN to `(30,34)`.
- Move RIGHT along Y=30 to reach `(30,49)`.
- **Collect Time Extender #2**: From `(30,49)`, go DOWN to `(35,49)` to collect the time extender. Backtrack UP to `(30,49)`.
- **Button**: Move UP from `(30,49)` to `(10,49)` and press the button.
- **Goal**: Once the button is pressed, the goal target appears in the bottom right (around `(50,54)` / `(51,55)`). Navigate down/right to reach it.

# Strategy to Win 
1. Collect first extender at `(5,34)`, backtrack left to `(5,29)`.
2. Follow downward/right serpentine path to `(30,49)`.
3. Move DOWN to `(35,49)` to pick up the second Time Extender! Backtrack UP to `(30,49)`.
4. Move UP to `(10,49)` to hit the button.
5. Pathfind DOWN and RIGHT to the goal destination at `(50,54)`.