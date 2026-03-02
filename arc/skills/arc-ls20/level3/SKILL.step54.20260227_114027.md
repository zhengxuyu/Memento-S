---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer**: Color 11 bar at the bottom. Decrements 2 cells per action.
- **Button**: Centered at Y=10, X=49.

# Level 3 Dead Ends & Blocks
- At `(15,34)`, UP and RIGHT are BLOCKED.
- At `(20,34)`, RIGHT is BLOCKED.

# Current Plan
- Moving DOWN to `(30,34)`.
- Previously at `(30,49)`, moved LEFT 3 times to `(30,34)`. 
- Need to reverse this: at `(30,34)`, I will move RIGHT 3 times back to `(30,49)`.
- From `(30,49)`, move UP to `(10,49)` to find the button.