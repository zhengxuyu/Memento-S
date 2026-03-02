---
name: "Level 1 & 2 Game Mechanics, Pathing and Strategies"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 U-shaped goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells.
- **Movement Steps**: Each movement action shifts the entire 5x5 block exactly 5 cells in the corresponding direction.
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position. Every wasted move costs 2 timer units.
- **Objectives**: A 3x3 U-shaped goal and a 3x3 gate-button.

# Target Coordinates for Level 2
- **Button**: 3x3 structure (colors 0 and 1) at Y=46..48, X=50..52. Target player top-left is Y=45, X=49 (centers over the button).
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.

# Current Strategy & Pathing
1. **Locate Objectives**: Identify the button and goal coordinates. For Level 2, the button is at (45, 49) and the goal is at (40, 14).
2. **Pathfind to the Button**: Move the block through valid 5x5 squares. Navigate around the start area and align along straight corridors (e.g., X=49). Moving downwards along that corridor leads directly to the button.
3. **Activate the Button**: Position the player exactly over the button to cover it (e.g., Y=45, X=49). The surrounding gate will physically change/open.
4. **Pathfind to the Goal**: Navigate back through the maze to the newly accessible goal.
5. **Enclose the Goal**: Move complete 5x5 player block perfectly over the 3x3 goal.

## Historical Data & Efficiency
- Level 1 typically completes in ~38-40 actions. 
- Level 2 has been completed in exactly 100 actions in previous attempts, which coincides with the maximum action / timer limit. This indicates that pathing perfectly without hitting walls or taking unnecessary detours is critical for Level 2 success.
- Hitting obstacles strictly penalizes the tight timer.

# Controls
- Action 1: Move UP (Y -= 5)
- Action 2: Move DOWN (Y += 5)
- Action 3: Move LEFT (X -= 5)
- Action 4: Move RIGHT (X += 5)