---
name: personal-subpersonal-distinction
description: >
  Separate agent-level explanations (what the agent does and why) from
  mechanism-level explanations (how the internal parts make it happen).
  Use when confusing what a system does with how it does it, or when
  you need to choose the right level of description for your current task.
---

# Personal/Sub-personal Distinction

There are two levels of explanation: *personal* (the whole agent — "the player wants to reach the goal") and *sub-personal* (internal mechanisms — "the pathfinding algorithm computes shortest routes"). Mixing these levels causes confusion. Each is valid for different purposes.

## When to Apply
- An explanation mixes agent-level and mechanism-level descriptions
- You need to decide which level of analysis is appropriate for your task
- Debugging: is the problem at the strategy level (wrong goal) or mechanism level (wrong execution)?
- Understanding why a correct strategy still produces wrong behavior

## Procedure
1. Identify the current explanation of a behavior or problem
2. Classify each claim as personal-level or sub-personal-level
3. Check for level-mixing: are mechanism details used to explain strategy, or vice versa?
4. Separate the levels: what does the agent want? How does the mechanism execute?
5. Address problems at the correct level — strategy problems need strategy fixes

## Example
"The agent failed because BFS chose the wrong path." This mixes levels. Personal: "The agent aimed for the wrong target." Sub-personal: "BFS correctly found the shortest path to the target it was given." The fix is at the personal level (choose a better target), not the sub-personal level (BFS is fine).

## Anti-Pattern
Don't insist on only one level of explanation. Both are needed. The error is mixing them in a single explanation, not using one or the other.
