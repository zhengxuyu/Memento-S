---
name: "Wall Avoidance"
description: "The c11 wall at rows 61-62 shrinks and expands as the player moves horizontally."
confirmed_count: 0
contradicted_count: 0
---
The bottom c11 wall located at rows 61-62 acts dynamically. Its left edge appears to correspond closely to the player's column.
- When player moves right, the left sections of the c11 wall disappear (it shrinks to only cover cols >= player's column approx).
- When player moves left, the c11 wall expands to the left again.
- Moving down near the right edge while the wall is shrunk might result in the player being shunted sideways if the wall expands and hits a carried block.
- A path downwards is completely blocked directly beneath the player so dropping straight down won't immediately reach rows 61-62 unless bypassing the right edge of c11.
