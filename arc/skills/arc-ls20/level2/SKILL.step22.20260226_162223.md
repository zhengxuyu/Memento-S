---
name: "Level 2: Explore and Pathfind"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is 1 cell per action. Wait, NO: movement is exactly 5x5 cells. Action 1: UP, Action 2: DOWN, Action 3: LEFT, Action 4: RIGHT.
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position.

# Target Coordinates for Level 2
- **Button**: 3x3 structure at Y=46..48, X=50..52. Target player top-left is Y=45, X=49.
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.

# Current Strategy & Pathing (Level 2)
1. Found path to button from intermediate (30, 34) is: UP x4, RIGHT x2, DOWN x1, RIGHT x1, DOWN x6.
2. After hitting the button, the gate will open.
3. Once button is matched, path to goal from (45, 49) to (40, 14).
