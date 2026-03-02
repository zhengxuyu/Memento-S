---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action. (ACTION1=UP, ACTION2=DOWN, ACTION3=LEFT, ACTION4=RIGHT)
- **Timer**: Color 11 bar at the bottom. Decrements 2 cells per action.
- **Time Extenders**: 3x3 Color 11 U-shapes add extra time! Pick them up if it's not too far out of the way.
- **Button**: Centered at Y=12, X=51. Target coordinates to trigger: Player top-left at Y=10, X=49.

# Level 3 Details & Pathing
- Dead Ends: `(15,34)` UP/RIGHT blocked; `(20,34)` RIGHT blocked.
- Escaped the right-side obstacles by going UP to `Y=30`.
- Current position: `(30, 39)`.
- Path to Button:
  - 2 moves RIGHT (ACTION4) to `(30, 49)`.
  - 4 moves UP (ACTION1) to `(10, 49)`. This lands perfectly on the button!
- Final Goal:
  - The gate will open after pressing the button.
  - Target for level completion: Top-left of avatar at `(50, 54)` to cover the goal `(51..53, 55..57)`.
