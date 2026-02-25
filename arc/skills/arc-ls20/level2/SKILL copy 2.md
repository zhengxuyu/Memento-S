---
name: "Scrolling Mechanics and Level Objects"
description: "Identification of player avatar, scrolling environment, and basic entities."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block consisting of colors 9 and 12. The top 2 rows are typically color 12, and the bottom 3 rows are color 9.
- **Movement**: The avatar moves exactly 5 cells per action (its own width and height), essentially snapping to a 5x5 grid.
- **Camera/Environment Scrolling**: Moving the player near the screen boundaries results in thousands of cells changing, which indicates a scrolling grid system. Moving the player within the screen boundaries without scrolling updates only the avatar's position (~50 cells).
- **Timer**: Color 11 acts as a timer, slowly depleting (turning into color 3). Fully depleting it causes a "time out" and a life lost. Note: Color 11 can also appear as 3x3 hollow structures in the map.
- **Blocked Moves**: When movement is blocked by an obstacle, the avatar's position does not update. The timer still updates (exactly 2 cells change, strictly 11->3). Note: Sometimes background animations or gates (e.g., color 0 changing to 5) may occur simultaneously, increasing the number of changed cells, but the lack of avatar movement confirms the block.
- **Lives**: Color 8 represents remaining lives. Displayed as small 2x2 blocks at the bottom right.
- **Levels/Score**: Reaching the level exit successfully completes the level and increments the score by 1. Keep progressing upwards.
- **Target/Goal**: The level exit is typically located towards the TOP of the level. Moving the avatar upwards through gaps in the walls is the most efficient way to finish the level.
- **Switches**: Small interactable objects (e.g., colors 0 and 1, often in a small cross or connected shape). Activating a switch removes specific colored barriers (like color 5 walls) to open up blocked paths.
- **Avatar Positioning**: The player avatar is strictly aligned to a 5x5 logical grid in relation to movement.

# Action Mappings
- ACTION1: UP
- ACTION2: DOWN
- ACTION3: LEFT
- ACTION4: RIGHT

# Next Steps & Strategies
- **Pathing**: The primary goal is the exit upward. If the direct path UP is open, take it. Do not prioritize the switch unless the path is strictly blocked by solid walls (color 5).
- **Detecting Obstacles**: If the avatar pixels do not change position after an action, the move was blocked by a wall or obstacle (usually you will see exactly 2 cells change for the timer). Immediately try moving in a different direction (UP, DOWN, LEFT, RIGHT) to bypass it. Do not repeat blocked actions.
- **Fast Completion**: The most efficient completions simply navigate UP and around obstacles, ignoring switches completely unless necessary. Navigate the maze-like structures while constantly prioritizing upward momentum and bypassing walls. A good level route takes advantage of the fact that moving directly to the top is the optimal strategy.
- **Example Route (Level 1)**: UP x3, LEFT x2, UP, LEFT x3, DOWN (to bypass), followed by UP/RIGHT zig-zags and finally UP straight to the goal. Vertical momentum is key to quickly traverse the scrolling map.