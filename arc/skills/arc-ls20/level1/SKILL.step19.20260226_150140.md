---
name: "Button and Gates"
description: "Navigate a player block to find and press buttons that open/close gates. Solve the routing puzzle to reach the goal and perfectly enclose it."
---

# Game Mechanics
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5 cells per action.
- Walkable area is primarily color 3. Colors 4 and 5 are obstacles/walls. 
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5) 
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases as moves are made. When the timer runs out, the episode ends (max_actions).

# Game Elements
- **Player Block**: 5x5 block. Movement is grid-aligned (5 cells at a time).
- **Goal Symbol**: A 3x3 symbol centered in a 5x5 space. Bounding box is 3x3 of color 9. Sometimes surrounded by a 7x7 structural gate.
- **Buttons / Keys**: Small cross-shape objects (colors 0 and 1) situated perfectly on the 5x5 grid intervals.
- **Gates**: Paths and the goal are protected by structural gates of color 5. 
- **Activation System**: 
  - Overlapping the player block *perfectly* over a button activates it.
  - Activating a button changes map features: it opens specific closed gates (changing them from 5 to 0) and can close other gates (from 0 to 5) concurrently.
  - Leaving a button does NOT automatically revert its gate. Gates stay open until another button causes them to close. The recent observation of the goal's gate closing (0->5) was caused by stepping *onto* a new button, not merely stepping off the previous one.
  - This turns the game into a combinatorial routing puzzle (a state machine): trigger the right sequence of buttons to open the path to the goal and ensure the overarching goal gate is open.

# Strategy
1. **Explore the Maze**: Traverse walkable terrain (color 3) in 5x5 increments to locate buttons and understand the network of gates.
2. **Pressing Buttons**: To activate a button, position the player's 5x5 block exactly over it. 
3. **Observe Map Changes**: When a button is pressed, observe which gates open (`5->0`) and which close (`0->5`). Use `run_code` mapping logic to systematically check diffs.
4. **Determine the Correct Sequence**: Map the dependencies. Find the button sequence that untangles the maze, opening the correct path segments iteratively until a complete open path exists to the goal, while leaving the goal's final 7x7 gate open.
5. **Enclose perfectly**: Travel to the final open gate and move the player exactly over the target 5x5 area circumscribing the 3x3 goal symbol (e.g. if goal is 11-13y, 35-37x, player must be at 10-14y, 34-38x) to trigger the level_up and win.