---
name: "Scrolling Mechanics and Level Objects"
description: "Navigate a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---
# How To Win (step-by-step)
1. Locate the button, identifying it as a small complex made of colors 0 and 1.
2. Move the player block onto the button to trigger it. This will open the gate by changing impassable walls (color 5) into passable terrain (colors 0 or 3).
3. Navigate efficiently towards the 3x3 goal symbol (color 9). Every move depletes the timer, so minimize wasted steps or dead ends.
4. Perfectly align the center 3x3 cells of your 5x5 player block over the 3x3 goal footprint.
5. Once aligned, perform 1 or 2 extra actions (like repeating the last movement into a wall) to force the game to register the alignment and complete the level.

# Controls
- Action 1: Move UP (moves exactly 5 cells)
- Action 2: Move DOWN (moves exactly 5 cells)
- Action 3: Move LEFT (moves exactly 5 cells)
- Action 4: Move RIGHT (moves exactly 5 cells)

# Key Facts
- The player avatar is a 5x5 block and moves by exactly its own width/height per action, effectively snapping to a 5x5 grid.
- The timer (color 11 at screen bottom) depletes by exactly 2 cells per action. Depleting it fully results in a time out and a life lost.
- Movement into obstacles (color 5 walls) is blocked. Your position will not change, but the timer will still deplete.
- Moving near the screen boundaries causes the environment to scroll.
- Remaining lives are shown as small 2x2 blocks of color 8 at the bottom right.