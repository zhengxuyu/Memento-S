---
name: computer-chess-marathon
description: >
  Distinguish between real-time performance under pressure and retrospective analysis at leisure.
  Use when conflating what an agent can do in the moment with what can be determined after the fact.
---

# A Computer Chess Marathon

A chess engine playing in real time under clock pressure makes different moves than the same engine analyzing the same positions with unlimited time afterward. This distinguishes competence-in-action from competence-in-reflection and warns against judging real-time performance by retrospective standards.

## When to Apply
- Evaluating an agent's real-time decisions using post-hoc analysis
- Someone says "the agent should have known X" when X was only discoverable with hindsight
- Confusing what is computable in principle with what is computable under time constraints

## Procedure
1. Identify the performance being evaluated
2. Determine the time and resource constraints under which it occurred
3. Compare with what an unconstrained analysis reveals
4. Ask: is the gap between real-time and retrospective performance a genuine failure or an expected consequence of resource limits?

## Example
An agent misses an optimal path in a game, and post-game analysis reveals it. The computer chess marathon reminds us: the agent had 300 steps and no lookahead, while the analyst has unlimited time. The "mistake" may have been rational under constraints.

## Anti-Pattern
Don't use this to excuse all errors. Some mistakes are avoidable even under real-time constraints. The tool distinguishes genuinely resource-limited failures from genuine incompetence.
