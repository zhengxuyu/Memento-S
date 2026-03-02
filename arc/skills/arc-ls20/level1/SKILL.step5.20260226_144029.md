---
name: "Button and Gates"
description: "Game involves navigating a 5x5 player block, stepping on a button to rotate a pattern display until it matches a goal pattern, which unlocks the path to the goal. Maximize score before the timer runs out. Completing a level advances to the next level."
---

# Game Mechanics
- Control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is 5 cells per action.
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5) 
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases 2 cells every move. When the timer runs out, the episode ends.
- Background is color 4, Walkable Path is color 3, Walls/Obstacles are color 5.

# Game Elements
- **Player Block**: A 5x5 avatar. Reference its top-left corner `(Y, X)` using the color 12 blocks.
- **Button / Key**: A small cross-shape object (colors 0 and 1). Overlapping it with the player block rotates the Pattern Display 90 degrees clockwise. You can move back and forth (e.g., Left then Right) to rotate it multiple times.
- **Pattern Display**: A 6x6 symbol at the bottom-left made of 2x2 blocks of color 9. It logically represents a 3x3 grid.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Goal Barrier**: A 7x7 structure of color 5 walls that surrounds the 3x3 goal area and its 5x5 frame. When the Display matches the Goal exactly, this 7x7 barrier opens up (turns from color 5 to walkable space).

# Strategy & Puzzle Logic
1. Locate the Button, the Pattern Display (bottom-left), and the Goal Symbol (top right/mid).
2. Look at the logical 3x3 representation in the Pattern Display (each 2x2 block is 1 cell of the 3x3 shape). 
3. **Compare to Goal**: Does the bottom-left Pattern Display ALREADY exactly match the shape of the Goal Symbol? 
   - If yes, **do not touch the button**. The path to the goal is already open. Pathfind directly to the goal to save time!
4. If patterns do not match, path to the button. Move back and forth on/off the button (e.g., ACTION3 then ACTION4) to rotate the display 90 degrees CW each time until the display EXACTLY matches the goal symbol. Wait for the barrier to open.
5. **Precise Overlap**: Pathfind precisely to overlap the 3x3 goal. 
   - Since movement is 5 cells per action, you will align step-by-step. The player's 5x5 bounds must completely enclose/align with the goal block.
6. Overlapping perfectly grants +1 score, immediately triggering a level-up or new spawn (grid completely resets for the next puzzle).