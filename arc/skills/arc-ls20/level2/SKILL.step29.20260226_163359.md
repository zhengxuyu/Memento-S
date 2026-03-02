---
name: "Level 2: Pathing to Button"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells. Action 1: UP, Action 2: DOWN, Action 3: LEFT, Action 4: RIGHT.
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position.

# Target Coordinates for Level 2
- **Button**: 3x3 structure at Y=46..48, X=50..52. Target player top-left is Y=45, X=49.
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.

# Current Strategy & Pathing (Level 2)
1. Path from start (45, 29) to intermediate (10, 34) observed: UP, RIGHT, UP, UP, UP, LEFT, UP, UP, RIGHT, UP.
2. After reaching (10, 34). We need to maneuver around obstacles to the button at (45, 49).
3. The remaining known path from (10, 34) is: RIGHT, RIGHT, DOWN, RIGHT, DOWN, DOWN, DOWN, DOWN, DOWN, DOWN.
4. After hitting the button perfectly (player top-left at 45, 49), the gate will open.
5. Once button is matched, path to goal from (45, 49) to (40, 14) must be calculated to finish the level.

## Historical Data
- Level 1 can be successfully completed in roughly 38 actions. Level 2 has been completed in ~100 actions in successful past episodes.

## Level 2 Cheat Sheet
1. **Locate Objectives**: Identify the Button (a 3x3 cross, colors 0 and 1) and the Goal (a 3x3 symbol, color 9) on the grid.
2. **Pathfind to the Button**: Plan a route to the button stepping ONLY on Walkable terrain (colors 0 and 3), completely avoiding Obstacles (colors 4 and 5). Note that every move jumps exactly 5 grid cells.
3. **Activate the Button**: Move your 5x5 player block exactly over the 5x5 area containing the Button to align their centers perfectly.
4. **Pathfind to the Goal**: Navigate off the button and travel toward the newly accessible Goal.
5. **Enclose the Goal**: Move complete 5x5 player block completely over the 3x3 Goal.

# Controls
- Action 1: Move UP (Y -= 5)
- Action 2: Move DOWN (Y += 5)
- Action 3: Move LEFT (X -= 5)
- Action 4: Move RIGHT (X += 5)