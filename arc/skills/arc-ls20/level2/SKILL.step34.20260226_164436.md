---
name: "Level 1 & 2 Game Mechanics, Pathing and Strategies"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 U-shaped goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells.
- **Movement Steps**: Each movement action shifts the entire 5x5 block exactly 5 cells in the corresponding direction.
- **Timer & Global Action Limit**: The episode has a strict global limit of 100 actions. Color 11 acts as a visual timer bar at the bottom, depleting by 2 cells per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position. 
- **Objectives**: A 3x3 U-shaped goal and a 3x3 gate-button.

# Target Coordinates for Level 2
- **Button**: 3x3 structure (colors 0 and 1) at Y=46..48, X=50..52. Target player top-left is Y=45, X=49 (centers over the button).
- **Goal**: 3x3 U-shape exactly at Y=41, X=15 (made of color 9). Target player top-left is Y=40, X=14.
- **Other Structures**: There are also 3x3 U-shapes made of color 11 at (16,15) and (51,30). These may be subsequent goals or secondary interactables.

# Current Strategy & Pathing
1. **Locate Objectives**: Identify the button and goal coordinates. For Level 2, the button is at (45, 49) and the main goal is at (40, 14).
2. **Pathfind to the Button**: Move the block through valid 5x5 squares. Navigate around the start area and align along straight corridors (e.g., X=49). Moving downwards along that corridor leads directly to the button.
3. **Activate the Button**: Position the player exactly over the button to cover it (Y=45, X=49). The surrounding gate will physically change/open.
4. **Pathfind to the Goal**: Navigate back through the maze to the newly accessible goal.
5. **Enclose the Goal**: Move the complete 5x5 player block perfectly over the 3x3 goal.

## Historical Data & Efficiency
- **Zero Margin for Error**: Level 1 typically completes in ~38 perfect actions. With the global limit of 100 actions per episode, this leaves only ~62 actions to finish Level 2. 
- In successful previous observations, Level 2 was completed on the *exactly* 100th action. Perfect pathing (no hitting walls, no unnecessary detours) is strictly mandatory to succeed. Every wasted move practically guarantees failure due to the total action limit.

# Controls
- Action 1: Move UP (Y -= 5)
- Action 2: Move DOWN (Y += 5)
- Action 3: Move LEFT (X -= 5)
- Action 4: Move RIGHT (X += 5)