---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds to the global action limit. They may be located in 5x5 dead ends, requiring you to backtrack after collecting. Also, the timer bar depletes exactly 2 cells of color 11 per action taken."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action.
- **Timer / Action Limit**: Color 11 bar at the bottom. Drains horizontally, converting exactly **2 cells of color 11 to color 3** per action taken. Remaining actions = (Remaining col 11 cells) / 2.
- **TIME EXTENDERS**: Stepping perfectly over 3x3 U-shapes made of color 11 ADDS to your timer (restores a chunk of color 11 cells). They are placed in 1-block dead ends, meaning you must collect and backtrack. Always collect them!

# Level 3 Route Info
- Start: (45,9)
- Collect Time Extender: ... -> (5,29) -> RIGHT -> (5,34) -> Dead end! Must go left back to (5,29).
- Path to Button: From (5,29), DOWN (ACTION2) to (10,29). Then straight RIGHT (ACTION4) x4 to (10,49).
- Button: Around (11,50). Pressing this button opens the gate near (46,31).
- Goal: A color 9 U-shape. Located at (51,55) to (53,57). Target top-left for goal intersection is (50,54).

# Strategy to Win 
1. If at (5,34) after collecting extender, move LEFT (ACTION3) back to main path at (5,29).
2. From (5,29), move DOWN (ACTION2) to (10,29).
3. From (10,29), straight RIGHT (ACTION4) x4 to (10,49) to press the button.
4. Once button is pressed at (10,49), gate at (46,31) opens.
5. Path back to gate: LEFT from (10,49) -> (10,29) -> DOWN to (45,29) -> RIGHT to (45,34) -> and through the opened gate! 
6. Move towards goal target top-left (50,54).
