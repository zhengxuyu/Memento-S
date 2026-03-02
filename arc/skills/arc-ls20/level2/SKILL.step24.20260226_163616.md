---
name: "Level 2: Pathing to Button and Goal"
description: "Mechanics and strategy for Level 2: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 U-shaped goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells per action.
- **Timer**: Color 11 acts as a timer, depleting by 2 cells per action.
- **Obstacles**: Colors 4 and 5. Moving into blocked cells consumes an action without changing position.
- **Button (Colors 0 & 1)**: Activating it swaps the state of specific dynamic gate obstacles (blocks changing between walkable and obstacle modes).

# Target Coordinates for Level 2
- **Button**: 3x3 structure (colors 0 and 1) at Y=46..48, X=50..52. Target player top-left is Y=45, X=49.
- **Goal**: 3x3 U-shape exactly at Y=41, X=15. Target player top-left is Y=40, X=14.

# Strategy & Pathing (Level 2)
1. **Locate Objectives**: The button is located at (45, 49) relative to the player's top-left, and the goal is at (40, 14).
2. **Move to Button**: Navigate via valid 5x5 steps to the right corridor (X=49) and move downwards (Y=45) to perfectly cover the button.
3. **Trigger Gate**: Positioning over the button shifts a gate (e.g., obstacles around Y=55 to Y=60 toggle states), opening a path towards the left.
4. **Move to Goal**: Head back out (upwards/leftwards) through the newly opened pathway directly to (40, 14).
5. **Win Condition**: Position the complete 5x5 player block over the 3x3 goal.

## Controls
- **Action 1**: Move UP (Y -= 5)
- **Action 2**: Move DOWN (Y += 5)
- **Action 3**: Move LEFT (X -= 5)
- **Action 4**: Move RIGHT (X += 5)

## Historical Data
- Level 1 typically finishes in ~38 actions. 
- Pathfinding requires precise alignment along a rigid 5x5 grid network—do not attempt moves that would clip into 5x5 grid-misaligned obstacles.
- Continuous downward toggling past the button can waste timer/actions; change direction directly after triggering the gate.
