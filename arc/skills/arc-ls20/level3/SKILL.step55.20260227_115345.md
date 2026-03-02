---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer**: Color 11 bar at the bottom. Decrements 2 cells per action.
- **Button**: Centered at Y=12, X=51. Target coordinates to trigger: Player top-left at Y=10, X=49.

# Level 3 Dead Ends & Blocks
- At `(15,34)`, UP and RIGHT are BLOCKED.
- At `(20,34)`, RIGHT is BLOCKED.

# Current Plan
- Reached `(30,34)`. Moving RIGHT to `(30,49)` (3 moves: ACTION4 x3).
- Then move UP to `(10,49)` (4 moves: ACTION1 x4) to stand on exactly the button!
- Once the button is pressed, the gate will open. The main goal is at Y=51, X=55 (Top left target: Y=50, X=54).
- Actually, since goal is `(51..53, 55..57)`, target is `(50,54)`.