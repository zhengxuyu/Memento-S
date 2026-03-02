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
- At `(15,34)`, moving RIGHT is BLOCKED. (Wasted action).
- At `(25,34)`, moving RIGHT is BLOCKED from going UP.

# Current Plan
- I am at `(15,34)` and tried going RIGHT, but it's blocked.
- So I need to try going UP from `(15,34)` to `(10,34)` or `(5,34)`, then right towards the button at `(10,49)`.
- Previously I was at `(30,49)` and went UP and LEFT. That lost my X=49 alignment.
- Let's move UP to `(10,34)` and see if RIGHT works.