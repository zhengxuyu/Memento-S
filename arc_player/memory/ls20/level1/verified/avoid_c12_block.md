---
name: "Avoid C12 Block Hypothesis"
description: "c12 blocks seem to restrict leftward movement when stepping on them directly. Better approach is to step away to another row, then move left."
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T10:34:51
---
Based on Step 107-112 where ACTION3 was continuously blocked on c12 at (30,34), it seems c12 limits horizontal movement. Moving UP/DOWN off the c12 block structure should unlock LEFT movement.

## ✓ Evidence #1 (2026-03-20T10:32:23)
Step 114-120: Moving from (25,34) DOWN to (30,34) then trying to move LEFT (ACTION3) was consistently blocked. Re-confirms that c12 at (30,34) prevents leftward movement.


## ✓ Evidence #2 (2026-03-20T10:34:51)
Step 17: Moved from (30,24) to (35,24) and tried right - blocked. From (30,24) tried right - blocked. The c9 block moves with us. The hypothesis that c12 blocks restrict movement but here the c9 block prevents rightward movement from col 24!
