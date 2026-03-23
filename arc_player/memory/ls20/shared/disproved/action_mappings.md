---
name: "Action mappings"
description: "Hypotheses about what buttons do"
confirmed_count: 4
contradicted_count: 6
verified_at: 2026-03-12T16:44:54
demoted_at: 2026-03-13T13:20:20
disproved_at: 2026-03-13T13:23:21
---
# Action Mappings
- ACTION1: Move UP
- ACTION2: Move DOWN
- ACTION3: Move LEFT
- ACTION4: Move RIGHT
- ACTION5: Unknown
- ACTION6: Unknown

The player is a 5x5 block. Top 2 rows are color 12, bottom 3 rows are color 9. It moves 5 cells per step.

## ✓ Evidence #1 (2026-03-12T16:44:43)
Step 2: ACTION2 moved player DOWN by 5 cells.


## ✓ Evidence #2 (2026-03-12T16:44:54)
Step 3: ACTION3 moved player LEFT by 5 cells.


## ✓ Evidence #3 (2026-03-12T16:45:27)
Step 12: Action 4 moved the player RIGHT from cols 19-23 to 24-28 (rows stayed 25-29). Confirms ACTION4 is RIGHT.


## ✓ Evidence #4 (2026-03-12T16:45:35)
Step 16: Actions 4 then 1 successfully moved the player right then up to (20-24,34-38), nearer target at (11,35). Confirms 1=UP, 4=RIGHT.


## ✗ Contradiction #1 (2026-03-13T13:16:58)
Step 62: Player avatar at (50,49), with object 9 at (52,49). Moving ACTION4 moved player right to (50,54) along with object 9 to (52,54). This contradicts any hypothesis that ACTION4 doesn't drag attached objects.


## ✗ Contradiction #2 (2026-03-13T13:17:25)
Step 64: At player avatar (50,54) and block (52,54), ACTION4 (RIGHT) was blocked. The map shows columns up to 63 exist, but right movement is blocked at col 58. Contradicts assumption that we can always move right if map is empty; there must be invisible or unmapped blockers.


## ✗ Contradiction #3 (2026-03-13T13:19:16)
Step 68: ACTION5 was tested at (40,49) expecting to trigger a switch or detach. Nothing happened, contradicting that ACTION5 and ACTION6 are alternative interaction buttons for detaching. They are either blocked directions or invalid.


## ✗ Contradiction #4 (2026-03-13T13:19:29)
Step 68: ACTION5 did nothing while player was at (40,49). It was blocked. Expected a possible swap or jump, but got nothing. Action mappings 5 and 6 remain non-functional or are conditionally blocked moves.


## ✗ Contradiction #5 (2026-03-13T13:20:20)
Step 70: ACTION3 blocked. It is mapped to move LEFT. However, there is NO visible object on the left. The player is at (35,49), cols to the left are 48, which are empty (c3). Yet movement was blocked. This contradicts the hypothesis that we only crash into colored walls like c11; we also crash into invisible walls or bounds for the attached c9 block.


## ✗ Contradiction #6 (2026-03-13T13:23:21)
Step 87: ACTION3 (LEFT) was repeatedly blocked at (30,49), which contradicts the idea that ACTION3 is always a valid move; we were hitting an obstruction.
