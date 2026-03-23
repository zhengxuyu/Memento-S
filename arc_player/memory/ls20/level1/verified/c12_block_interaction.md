---
name: "c12 block interaction"
description: "Interaction with c12 blocks"
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T10:38:15
---

When the player is on a c12 block, it appears that certain actions are blocked. Specifically, when at position (30,34), which is on a c12 block, ACTION3 (LEFT) is consistently blocked.

## ✓ Evidence #1 (2026-03-20T10:36:23)
Step 21-22: Moving LEFT from (30,34) on c12 block was blocked again. This confirms that stepping on the c12 block directly severely limits movement to certain directions like LEFT.


## ✓ Evidence #2 (2026-03-20T10:38:15)
Step 28: ACTION1 at (15,34) was blocked, likely because the c12 player interacts with the c9 lock or other blocks. Confirms interaction between c12 blocks and static elements, preventing movement when blocked.
