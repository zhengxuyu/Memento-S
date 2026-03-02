---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Detailed pathing for Level 3, tracking dead ends and the exact route to reach the button/goal."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1 (UP), ACTION2 (DOWN), ACTION3 (LEFT), ACTION4 (RIGHT). Moves exactly 5 cells. Costs 1 action.
- **Timer / Action Limit**: Color 11 bar at the bottom.
- **Time Extenders**: 3x3 U-shapes of color 11. Picking them up adds to the global action limit.

# Level 3 Route Discovery
- Start: (45,9)
- Collect Time Extender: ... -> (5,29) -> RIGHT -> (5,34)
- **Dead end at (5,34)**. Must go left back to (5,29).
- From (5,29) -> DOWN -> (10,29).
- At (10,29), RIGHT is blocked!
- From (10,29) -> DOWN -> (15,29).
- From (15,29) -> RIGHT -> (15,34).
- At (15,34), RIGHT is blocked!
- From (15,34) -> DOWN -> (20,34).
- At (20,34), RIGHT is blocked!
- From (20,34) -> DOWN -> (25,34).
- From (25,34), the path branches RIGHT. We explored:
  - (25,49): UP is blocked.
  - (25,44): UP is blocked.
  - (25,39): UP is blocked.
- Since UP is blocked at X=39, X=44, and X=49, we must backtrack further. The next logical step is to see if we navigate DOWN from (25,34), or backtrack back left or up.

# Goal Locations
- Button/Key: (10, 49) - Color 0/1 area.
- Gate/Lock: (46, 31) - Color 0/14 area.
- Goal Exit: Top-left at (50, 54) - Color 9/12 U-shape.

# Strategy to Win 
1. Collect extender at (5,34), backtrack left to (5,29).
2. Follow downward/right serpentine path to (25,34).
3. Backtrack through dead ends on the X-axis (X=49, X=44, X=39 are blocked going UP).
4. Find the correct vertical corridor that allows UP to reach Y=10 and cross over to the button at (10,49).
5. Open gate at (46,31).
6. Reach Goal at (50,54).
