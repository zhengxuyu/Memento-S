---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer**: Color 11 bar at the bottom.
- **Button**: Centered at Y=10, X=49.

# Level 3 Route Info
- Start: `(45,9)`
- Collect Time Extender #1: `... -> (5,29) -> RIGHT -> (5,34)` -> Dead end. Backtrack LEFT to `(5,29)`.
- Nav DOWN: `(10,29)` (RIGHT blocked), `(15,29)`, RIGHT to `(15,34)`.
- DOWN to `(25,34)`. At `(25,34)`, RIGHT paths to X=39,44,49 are blocked from going UP.
- DOWN to `(30,34)`, RIGHT to `(30,49)`.
- **Collect Time Extender #2**: DOWN to `(35,49)` and back UP to `(30,49)`.

# Path to Button at (10,49)
1. Since Y=25, X=49 is blocked from going UP, navigate from `(25,49)` LEFT to `(25,34)`. Just reached (25, 39), need one more step LEFT to (25, 34).
2. From `(25,34)`, move UP to `(15,34)`.
3. From `(15,34)`, move RIGHT to `(15,49)`.
4. From `(15,49)`, move UP to `(10,49)` to press the button.
5. After pressing the button, pathfind to the goal at `(50,54)`. (Likely via backtracking).