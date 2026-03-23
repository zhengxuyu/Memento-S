---
name: "pattern-match-scoring"
description: "When the remote pattern MATCHES a target pattern"
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T11:01:08
---

When the c9 shape at the bottom-left perfectly matches the c9 shape at the top-left, perhaps scoring should happen if I press a specific 'submit' button?
Wait, if stepping on (30,19) toggles states, and I matched the top-left U-shape, but my score stayed 0, maybe I needed to touch the goals.
But when I stepped off (30,19) by doing ACTION1, the entire world cleared to color 11.
Could this be because cycling it ONE MORE time past the target configuration triggers a penalty/fail state?
Or stepping off when it is perfectly matched triggers a fail state?
Let's figure out if color 11 means fail or pass.
If score=0, it probably means fail.
Conclusion:
- Do not step off the button when c11 is totally gone or match is perfect?
- Or wait, what if the goal was NOT to completely eliminate c11?
- Maybe c11 was a barrier keeping back some hazard? No hazards seen.
- Maybe there is a specific step sequence required, and any deviation causes failure?
I will confirm with tests.

## ✓ Evidence #1 (2026-03-20T11:00:09)
Step 20: ACTION1 to step onto the button at (30,19). The 9 blocks at (57,4) changed. Stepping on and off the button cycles the pattern.


## ✓ Evidence #2 (2026-03-20T11:01:08)
Step 28: ACTION1 to step onto the button at (30,19). The c9 pattern at (55,3) cycles again but in a different state. It seems to be a complex sequence or something else is needed.
