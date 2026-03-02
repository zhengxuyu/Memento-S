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
- Currently at (20,34), testing movement to navigate toward button. 
- Button target is at Y=10, X=49.

# Strategy to Win 
1. If at (5,34) after collecting extender, move LEFT (ACTION3) back to main path at (5,29).
2. From (5,29), move DOWN (ACTION2) to (10,29).
3. At (10,29), right blocked. DOWN to (15,29).
4. RIGHT to (15,34). RIGHT blocked. DOWN to (20,34).
5. From (20,34), continue navigating to reach the button at (10,49).
6. Open gate at (46,31), Goal target top-left is (50,54).
