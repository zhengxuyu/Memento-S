---
name: "Level 2: Pathing to Button and Goal"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 U-shaped goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells. Action 1: UP, Action 2: DOWN, Action 3: LEFT, Action 4: RIGHT.
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position.

# Target Coordinates for Level 2
- **Button**: 3x3 structure (colors 0 and 1) at Y=46..48, X=50..52. Target player top-left is Y=45, X=49.
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.

# Current Strategy & Pathing (Level 2)
1. **Locate Objectives**: The button is at (45, 49) and goal is at (40, 14).
2. **Pathfind to the Button**: Move the block through valid 5x5 squares. Currently, we navigate around the start area and align along the right side corridor at X=49. Moving downwards along X=49 leads directly to the button.
3. **Activate the Button**: Position the player exactly at Y=45, X=49 to cover the button. The surrounding gate will physically change/open upon successful activation.
4. **Pathfind to the Goal**: After pushing the button, navigate leftward and upward back to the newly accessible goal at Y=40, X=14.
5. **Enclose the Goal**: Move complete 5x5 player block perfectly over the 3x3 goal.

## Historical Data
- Level 1 typically takes ~38 actions. 
- Level 2 has been completed at action 100 in previous successful attempts.
- Effective pathing requires taking advantage of straightaways like the corridor at X=49 once aligned properly.

# Controls
- Action 1: Move UP (Y -= 5)
- Action 2: Move DOWN (Y += 5)
- Action 3: Move LEFT (X -= 5)
- Action 4: Move RIGHT (X += 5)
