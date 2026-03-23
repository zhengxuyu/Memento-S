---
name: "Player carries c9 object"
description: "The player (c12) carries the c9 object located in its 5x5 block."
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T10:36:45
---
The player is composed of c12 pixels in the top 2 rows of a 5x5 block, and a c9 object is in the bottom 3 rows. They move together as a single unit.

## ✓ Evidence #1 (2026-03-20T10:36:28)
Step 4-6: ACTION3 moved player (c12) from (30,44) to (30,34). The c9 object at (32,44)-(34,48) moved with it to (32,34)-(34,38).


## ✓ Evidence #2 (2026-03-20T10:36:45)
Step 8-10: Actions moved player from (30,34) to (25,24) with c9 block directly below it, which moved from (32,34)-(34,38) to (27,24)-(29,28).
