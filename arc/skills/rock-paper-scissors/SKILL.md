---
name: rock-paper-scissors
description: >
  Analyze non-transitive dominance and mixed strategies under uncertainty.
  Use when ranking or comparison assumes a simple linear ordering that doesn't exist.
---

# Rock, Paper, Scissors

In some competitive situations, no single strategy dominates all others. A beats B, B beats C, but C beats A. Rational play requires mixed strategies — randomness is a feature, not a bug. This applies whenever dominance relations are cyclic.

## When to Apply
- A ranking or comparison assumes a linear "best to worst" ordering
- Someone seeks "the best strategy" in a domain with cyclic dominance
- An agent is being exploited because it plays a predictable pure strategy

## Procedure
1. Identify the strategies or options being compared
2. Check whether dominance is transitive (A > B > C implies A > C) or cyclic
3. If cyclic, recognize that no pure strategy is optimal
4. Consider whether randomization or diversity of approach is needed

## Example
An agent tries three exploration strategies: random walk beats wall-following in open spaces, wall-following beats systematic sweep in mazes, systematic sweep beats random walk in structured rooms. There is no single "best" — the agent should adapt or mix strategies.

## Anti-Pattern
Don't invoke this whenever there's any competition. It specifically applies to non-transitive dominance, not all strategic situations.
