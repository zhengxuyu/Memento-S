---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Navigating Level 3: Moving RIGHT along Y=10 corridor."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Fog of War**: Moving into unrevealed areas clears color 4.
- **Action Mappings**: 
  - ACTION1: Move UP (Y - 5)
  - ACTION2: Move DOWN (Y + 5)
  - ACTION3: Move LEFT (X - 5)
  - ACTION4: Move RIGHT (X + 5)
- **Timer**: Episodic global limit of 100 actions. Color 11 at bottom depletes by 2 cells per action.

# Level 3 Route Info
- Start: (45,9)
- Moved UP to Y=10.
- Currently moving RIGHT (ACTION4) from X=9 to X=49.
- Button: Covers (11-13, 50-52). Target player pos: (10,49).
- Goal: Covers (51-53, 55-57). Target player pos: (50,54).

# Strategy to Win 
1. Strict 5x5-aligned moves avoiding obstacle walls (color 5).
2. Move over the 3x3 button (0/1 colors) to open the gate.
3. Path perfectly to goal and center player block over the 3x3 U-shaped goal (color 9).