---
name: "Button Alignment Challenge Level 2 Tracker"
description: "Track navigation through the built-in maze to reach the target horseshoe."
---

# Game Mechanics
- **Player Block**: We control a 5x5 block, top 2 rows color 12, bottom 3 rows color 9. Step size is 5 cells.
- **Controls**: ACTION1 (Up), ACTION2 (Down), ACTION3 (Left), ACTION4 (Right).
- **Obstacles**: Color 5 acts as impassable terrain.
- **Timer**: Color 11 at the bottom decreases by 2 cells every move.

# Level 2 Details
- **Goal Position**: Y=41..43, X=15..17 (A 3x3 horseshoe of color 9). Target placement for our 5x5 block top-left is Y=40, X=14.
- **Other objects**: Color 11 O-shapes are TIME BONUSES! I grabbed one at (51,30) and the timer increased! (There's another at 16,15).
- **Button Position**: Y=46..48, X=50..52 (Color 0 and 1 structure). Center X=51.

# Current Path Taken
At (45, 44), LEFT failed.
Moved DOWN to (50, 44).
LEFT to (50, 39).
LEFT to (50, 34).
LEFT to (50, 29). Hit the O-shape, restored timer. But it's a dead end! Left, Up, Down all failed.
Next: move RIGHT to (50, 34) and try a different path (maybe UP or DOWN from 34 or 39).