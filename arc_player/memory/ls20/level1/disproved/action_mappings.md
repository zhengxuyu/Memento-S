---
name: "Action mappings"
description: "Hypotheses about what buttons do"
confirmed_count: 2
contradicted_count: 4
verified_at: 2026-03-19T13:42:47
demoted_at: 2026-03-19T13:54:04
disproved_at: 2026-03-19T13:58:40
---

- ACTION1: UP
- ACTION2: DOWN
- ACTION3: LEFT
- ACTION4: RIGHT
- ACTION5: ???
- ACTION6: ???

## ✓ Evidence #1 (2026-03-19T13:42:32)
Step 113: Player at (25,24) used ACTION2 and moved to (30,24). This confirms ACTION2 is DOWN.


## ✓ Evidence #2 (2026-03-19T13:42:47)
Step 116, Player at (30,24) used ACTION3 and moved to (30,19). This confirms ACTION3 is LEFT.


## ✗ Contradiction #1 (2026-03-19T13:46:54)
Step 20: ACTION3 at player (30,34) resulted in being blocked, not moving left. There appears to be an invisible wall, as there's no visible obstacle.


## ✗ Contradiction #2 (2026-03-19T13:51:32)
Step 53: I have been repeatedly blocked from moving left from (30,34) even though the nav map says I should be able to. I suspect the c9 blocks are actually a wall.


## ✗ Contradiction #3 (2026-03-19T13:54:04)
Step 57: ACTION3 (LEFT) is still blocked at (30,34) despite the nav map showing it is open. This has happened for 5 consecutive steps.


## ✗ Contradiction #4 (2026-03-19T13:58:40)
Step 126: ACTION3 at player (30,34) was blocked. There is a c9 wall to the right, but nothing to the left. The action should have succeeded.
