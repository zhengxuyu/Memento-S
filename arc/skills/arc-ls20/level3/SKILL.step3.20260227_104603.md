---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Navigating Level 3: Moving UP left corridor. Currently at Y=35."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Fog of War**: Moving into unrevealed areas clears color 4.
- **Action Mappings**: 
  - ACTION1: Move UP (Y - 5)
  - ACTION2: Move DOWN (Y + 5)
  - ACTION3: Move LEFT (X - 5)
  - ACTION4: Move RIGHT (X + 5)
- **Timer**: Episodic global limit of 100 actions. Color 11 at bottom depletes by 2 cells per action. Currently observing color 11 decreasing at col 14.

# Level 3 Route Info
- Start: (45,9)
- Action 1 to (40,9) cleared Fog
- Action 1 to (35,9)
- Continue ACTION1 until Y=5, then move RIGHT towards button.
- Button: (10,49).
- Goal: (50,54).

# How To Win 
1. Strict 5x5-aligned moves avoiding obstacle walls (color 5).
2. Move over the 3x3 button (0/1 colors) to open the gate.
3. Path perfectly to goal and center player block over the 3x3 U-shaped goal (color 9).