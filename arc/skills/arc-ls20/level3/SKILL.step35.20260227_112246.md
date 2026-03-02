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
- From (25,44), RIGHT -> (25,49).

# Exploring Alternatives to reach Button
- Button top-left coordinate is (10, 49).
- Attempted going UP from (25,49) -> Blocked.
- Backtracked left to (25,44), attempted going UP -> Blocked!
- Now backtracking left to (25,39), will attempt going UP.

# Strategy to Win 
1. Collect extender at (5,34), backtrack left to (5,29).
2. Follow downward/right serpentine path to (25,39).
3. Try UP at X=39.
4. Eventually open gate at (46,31), Goal top-left is (50,54).