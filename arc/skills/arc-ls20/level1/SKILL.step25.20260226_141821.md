---
name: "Button and Gates"
description: "Game involves navigating a 5x5 player block, stepping on a button to rotate a pattern display until it matches a goal pattern, which unlocks the path to the goal. Maximize score before the timer runs out."
---

# Game Mechanics
- Control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is 1 cell per action.
- Action 1: UP (Y -= 1)
- Action 2: DOWN (Y -= 1) => WAIT, Action 1 is UP, Action 2 is DOWN, Action 3 is LEFT, Action 4 is RIGHT. (Note: in earlier games it was step 5, here it is 1).
- Action 3: LEFT (X -= 1)
- Action 4: RIGHT (X += 1)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases exactly 2 cells every move. When the timer runs out (max actions), the episode ends. 

# Game Elements
- **Player Block**: A 5x5 avatar.
- **Button / Key**: A small cross-shape object (colors 0 and 1). Stepping on it (overlapping with player block) rotates the Pattern Display 90 degrees clockwise.
- **Pattern Display**: A 6x6 symbol at the bottom-left made of 2x2 blocks of color 9. It logically represents a 3x3 grid.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Goal Barrier**: A 7x7 structure of color 5 walls that surrounds the 3x3 goal area and its 5x5 frame. When the Display matches the Goal exactly, this 7x7 barrier opens up (turns from 5 to 0).

# Strategy & Puzzle Logic
1. Locate the Button, the Pattern Display (bottom-left), and the Goal Symbol (top-right or top-mid).
2. Look at the logical 3x3 representation in the Pattern Display (each 2x2 block is 1 cell of the 3x3 shape). 
3. **Compare to Goal**: Does the bottom-left Pattern Display ALREADY exactly match the shape of the Goal Symbol? 
   - If yes, **do not touch the button**. The path to the goal should already be open. Path directly to the goal to save time!! Stepping on the button will CLOSE the barrier.
4. If patterns do not match, path to the button. Move back and forth on/off the button to rotate the display 90 degrees CW each time until the display EXACTLY matches the goal symbol. Visualizing the rotation: a 90-degree CW rotation turns the top row of the display into the right column.
5. Once the pattern matches, a large-scale change will occur, deleting the color 5 barrier (7x7 outer frame) around the Goal.
6. **Precise Overlap**: Pathfind precisely to overlap the 3x3 goal. 
   - For a perfect overlap, the top-left corner of your 5x5 footprint must be exactly `(Goal_Y - 2, Goal_X - 1)`.
   - Example: if the goal's top-left is `(11, 35)`, your player's top-left point `(player_y, player_x)` must rest exactly at `(9, 34)`.
   - NOTE: Inner 5x5 color 5 blocks might exist. Simply attempt to walk onto the goal to align.
7. Overlapping perfectly grants +1 score, immediately triggering a level-up.