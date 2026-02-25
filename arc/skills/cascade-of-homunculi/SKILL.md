---
name: cascade-of-homunculi
description: >
  Decompose intelligent behavior into progressively simpler sub-processes
  until each component is "stupid" enough to be mechanical. Use when
  explaining complex behavior, designing systems, or breaking down a
  difficult task into manageable sub-tasks that don't require intelligence.
---

# A Cascade of Homunculi

The homunculus fallacy says you can't explain cognition by positing a little person inside the head — that just pushes the problem back. Dennett's solution: you *can* use homunculi if each layer is *stupider* than the one above, until you reach components so simple they're just mechanisms. Intelligence emerges from organized stupidity.

## When to Apply
- Breaking a complex task into sub-tasks
- Explaining how a system produces intelligent-seeming behavior
- Designing a multi-layer architecture where each layer handles less
- When a proposed explanation just restates the problem at a smaller scale

## Procedure
1. Identify the intelligent behavior to be explained or implemented
2. Decompose it into 2-4 sub-tasks, each requiring less intelligence
3. For each sub-task, ask: is this simple enough to be mechanical/algorithmic?
4. If not, decompose further until each component is a simple, dumb operation
5. Verify: do the dumb components, composed together, produce the intelligent behavior?

## Example
Task: "Score points in an unknown game." Decompose: (1) Map actions to effects (mechanical: try each action, record result). (2) Identify objects (mechanical: scan grid for non-background colors). (3) Test interactions (mechanical: move to each object, try actions). (4) Record what changes score (mechanical: compare score before/after). Each sub-task is simple; together they produce game-learning behavior.

## Anti-Pattern
Don't decompose into sub-tasks that are just as hard as the original. "Understand the game" decomposed into "figure out the rules" is not progress — it's the homunculus fallacy. Each level must be genuinely simpler.
