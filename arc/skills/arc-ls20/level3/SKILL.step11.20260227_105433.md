---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Navigating Level 3: Reached Y=5, X=14. Continuing RIGHT."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Fog of War**: Moving into unrevealed areas clears color 4.
- **Action Mappings**: 
  - ACTION1: Move UP (Y - 5)
  - ACTION2: Move DOWN (Y + 5)
  - ACTION3: Move LEFT (X - 5)
  - ACTION4: Move RIGHT (X + 5)
- **Timer**: Episodic global limit of 100 actions. Color 11 at bottom depletes by 2 actions.

# Level 3 Route Info
- Start: (45,9)
- Moved UP 8 times to Y=5, X=9.
- Moved RIGHT 1 time to Y=5, X=14.
- Button: Covers (11-13, 50-52). Target player pos: (10,49).

# Strategy to Win 
1. Strict 5x5 alignments avoiding obstacle walls (color 5).
2. Path goes ALL the way up to Y=5. Traversing RIGHT (ACTION4) towards X=49. Once at X=49, it will be time to move DOWN to trigger the button.