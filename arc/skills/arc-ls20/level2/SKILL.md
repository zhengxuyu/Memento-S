---
name: "Level 2 Investigation"
description: "Collecting fuel, navigating a maze"
---
# Rules & Mechanics
- **Fuel / Timer**: The game has a timer. Color 11 blocks slowly disappear. When they do, the screen flashes (Grid 0 turns all color 11) and you lose a life.
- **Lives**: Color 8 blocks in bottom right are your lives. Starts with 3 lives (12 blocks, 3x 2x2 squares). When you die, a 2x2 square is removed, and you respawn at the start.
- **Respawn Point**: (40,29).
- **Goal**: Reach the exit at (46,50) (composed of colors 0 and 1) BEFORE the timer runs out!

# Actions
- Action 1: UP (-5 row)
- Action 2: DOWN (+5 row)
- Action 3: LEFT (-5 col)
- Action 4: RIGHT (+5 col)

# Strategy for Level 2
- The exit is at (46,50). I am starting at (40,29).
- PATH SO FAR:
  - (40,29) -> R -> (40,34) 
  - (40,34) -> U -> (35,34)
  - (35,34) -> U -> (30,34)
  - (30,34) -> R -> (30,39)
  - (30,39) -> U -> (25,39)
  - (25,39) -> L -> (25,34)
- BLOCKED PATHS DISCOVERED:
  - R from (40,34) is BLOCKED.
  - R from (35,34) is BLOCKED.
  - R from (30,39) is BLOCKED.
  - R from (25,39) is BLOCKED.
  - U from (25,39) is BLOCKED.
  - L from (25,34) is BLOCKED.
- NEXT STEP: 
  - Try moving UP from (25,34) to (20,34).