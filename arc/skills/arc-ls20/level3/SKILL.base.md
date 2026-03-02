---
name: "ARC-AGI-3 Core Mechanics"
description: "Find and activate the button to open the path to the final goal."
---
# How To Win (step-by-step)
1. Scan the grid to locate the 'button' structure.
2. Navigate the 5x5 player block to perfectly cover the button. This will change the level layout, opening a new path.
3. Locate the now-accessible U-shaped 'goal' structure.
4. Pathfind a route for the player block to the goal.
5. Position the 5x5 player block to perfectly cover the 3x3 goal structure to win.

# Controls
- Action 1: Move UP (Y -= 5)
- Action 2: Move DOWN (Y += 5)
- Action 3: Move LEFT (X -= 5)
- Action 4: Move RIGHT (X += 5)

# Key Facts
- The player is a 5x5 block and all movement is in 5-cell increments.
- A strict, global action limit is always active. Wasting moves by hitting walls will likely cause you to fail.
- Interacting with objects (buttons, goals) requires the 5x5 player block to be positioned perfectly over them.
