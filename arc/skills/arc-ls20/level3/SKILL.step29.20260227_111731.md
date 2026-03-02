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
- From (25,34), RIGHT -> (25,39).
- From (25,39), RIGHT -> (25,44).
- Trying RIGHT from (25,44) and hopefully reaching (25,49).

# Strategy to Win 
1. If at (5,34) after collecting extender, move LEFT (ACTION3) back to main path at (5,29).
2. From (5,29), move DOWN (ACTION2) to (10,29).
3. At (10,29), right blocked. DOWN to (15,29).
4. RIGHT to (15,34). RIGHT blocked. DOWN to (20,34).
5. RIGHT blocked at (20,34). DOWN to (25,34).
6. At (25,34), RIGHT to (25,39) -> RIGHT to (25,44).
7. Goal is to reach X=49, then UP to Y=10.
8. Open gate at (46,31), Goal target top-left is (50,54).