---
name: "Level 2: Explore and Pathfind"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: 5 cells per action. Action 1: UP, Action 2: DOWN, Action 3: LEFT, Action 4: RIGHT.
- **Scroll**: Screen bounds can scroll (e.g. Action 1 near map top moves camera, updating 1500+ cells).
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.

# Strategy & Pathing
1. Move the player block onto the button (color 0/1) to unlock the path.
2. Navigate towards the goal (color 9).
3. Center perfectly over the 3x3 goal. 

# Level 2 Details
- **Button**: at Y=47, X=50 (bounding top-left at 45, 49)
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.
- Player top-left is currently Y=25, X=34.
- Remaining path to button: UP*3, RIGHT*2, DOWN, RIGHT, DOWN*6.
- Executing UP now.
