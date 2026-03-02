---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds to the global action limit. They may be located in 5x5 dead ends, requiring you to backtrack after collecting."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer / Action Limit**: Color 11 bar at the bottom.

# Level 3 Route Info
- Start: (45,9)
- Collect Time Extender: ... -> (5,29) -> RIGHT -> (5,34) -> Dead end! Must go left back to (5,29).
- After backtracking to (5,29), going DOWN -> (10,29).
- At (10,29), RIGHT is blocked!
- From (10,29), moved DOWN to (15,29).
- From (15,29), moved RIGHT to (15,34).
- At (15,34), RIGHT blocked, moved DOWN to (20,34).
- At (20,34), RIGHT blocked, moved DOWN to (25,34).
- **From (25,34), explored:**
  - RIGHT paths to X=39,44,49 are blocked from going UP.
  - DOWN -> (30,34) works!
  - From (30,34), went RIGHT -> (30,39).

# Strategy to Win 
1. Collect extender at (5,34), backtrack left to (5,29).
2. Follow downward/right serpentine path to (25,34) and then DOWN to (30,34).
3. Move RIGHT along Y=30 to reach the X-column of the button (X=49).
4. Go UP to button at X=49, Y=10.
5. Goal top-left is (50,54).