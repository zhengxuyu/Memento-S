---
name: "Level 2 Timer and Reset"
description: "Failing the level before the c11 timer runs out results in a full reset to (35,29)."
confirmed_count: 0
contradicted_count: 0
---
Hypothesis:
In Level 2, the set of c11 blocks acts as a countdown timer, shrinking every time we press the pattern button.
If the timer runs out before we achieve the goal, the level fills with c11 (fail state).
Any action taken from the fail state resets the player back to the starting position of Level 2 at (35,29).
We must match the target pattern AND do something else (like step on a submit button, possibly c8 at 61,56) before the timer runs out.