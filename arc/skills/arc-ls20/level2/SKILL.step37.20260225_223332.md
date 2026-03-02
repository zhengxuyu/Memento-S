---
name: "Scrolling Mechanics and Level Objects - Button Alignment Challenge"
description: "Navigate a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block. Top 2 rows are color 12, bottom 3 rows are color 9. The center of the avatar is the exact middle pixel.
- **Movement**: The avatar moves exactly 5 cells per action (its own width and height), essentially snapping to a 5x5 grid.
  - Action 1: Move UP (Y decreases by 5 cells)
  - Action 2: Move DOWN (Y increases by 5 cells)
  - Action 3: Move LEFT (X decreases by 5 cells)
  - Action 4: Move RIGHT (X increases by 5 cells)
- **Camera/Environment Scrolling**: Moving the player near the screen boundaries can cause thousands of cells to change, indicating a scrolling grid system. Within screen boundaries, ~50 cells update.
- **Timer**: Color 11 acts as a timer at the bottom of the screen, depleting to color 3. Exactly 2 cells change per action. Fully depleting it causes "time out" and life lost. Do not waste moves!
- **Blocked Moves**: When movement is blocked by an obstacle (color 5 walls), the avatar's position does not update. The timer still updates (2 cells change). Reverse direction if this happens.
- **Lives**: Color 8 represents remaining lives as small 2x2 blocks at the bottom right.
- **Button / Key**: Objects made of color 0 and 1 arranged in a small complex. When the 5x5 player steps on (overlaps) these objects, they act as switches, turning impassable terrain (color 5) into passable color 0 or 3. Opening the gate changes ~120 cells globally!
- **Gates / Obstacles**: Color 5 acts as impassable terrain.
- **Goal / Alignment**: A 3x3 symbol made of color 9 on the grid. To complete a level, perfectly align the **center 3x3 cells of the 5x5 player block** precisely over the 3x3 goal footprint. Wait 1 extra action (e.g., repeating the last movement) for the game to register the alignment.

# Strategy & Pathing
1. Locate the button (small complex of colors 0 and 1).
2. Move the player block onto the button to unlock the path.
3. Navigate your player block efficiently towards the goal.
4. Center your 5x5 player block perfectly over the 3x3 goal to complete the level. 

# Level 2 Details
- **Start**: Avatar center at Y=37, X=31.
- **Button**: at Y=47, X=51.
- **Goal**: at Y=42, X=16.
- **Path to Button**:
  - The direct route is blocked. You must move North to Y=12.
  - Path from start: LEFT, UP, UP, UP (to 12, 36), RIGHT, RIGHT (to 12, 46), DOWN (to 17, 46), RIGHT (to 17, 51), DOWN x 6 (to 47, 51).
  - Current Position: (27, 51) - moving DOWN towards the button.