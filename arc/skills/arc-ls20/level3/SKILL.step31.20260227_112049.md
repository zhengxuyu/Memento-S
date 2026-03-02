---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds to the global action limit. Backtracking is sometimes required."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action. (ACTION1=UP, ACTION2=DOWN, ACTION3=LEFT, ACTION4=RIGHT).
- **Timer / Action Limit**: Color 11 bar at the bottom. Decreases every action, increases when you collect a 3x3 Color 11 U-shape (Time Extender).

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

# Targeting Button
- Button is at (11..13, 50..52). Center is (12, 51).
- The player center needs to step on the button center.
- Since player is 5x5, its top-left coordinate should be (10, 49).
- From (25, 49), move UP x 3 to reach (10, 49). Pressing it opens the gate at (46,31).

# Route from Button to Goal
- Once the gate opens, you must navigate from (10, 49) to the gate at (46,31).
- Goal target (color 8 structure) top-left is at (50,54).
- You can either check if a southbound path from (25,49) exists or backtrack the way you came all the way to columns 29/34, then head south towards row 45/50 to reach the gate.

# Strategy to Win 
1. Reach Time Extender at (5,34), then move LEFT (ACTION3) back to main path at (5,29).
2. From (5,29), move DOWN (ACTION2) to (10,29).
3. At (10,29), right blocked. DOWN to (15,29).
4. RIGHT to (15,34). RIGHT blocked. DOWN to (20,34).
5. RIGHT blocked at (20,34). DOWN to (25,34).
6. At (25,34), RIGHT to (25,39) -> RIGHT to (25,44) -> RIGHT to (25,49).
7. UP x3 to (10,49). Button is pressed. Gate at (46,31) opens.
8. Navigate back to the gate (46,31). Pathfind downwards and westwards.
9. Enter gate, align player with Goal target top-left (50,54).
