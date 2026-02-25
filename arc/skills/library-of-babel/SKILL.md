---
name: library-of-babel
description: >
  Recognize that searching vast possibility spaces requires heuristics, not
  exhaustive enumeration. Use when facing a combinatorial explosion of options.
---

# Leaping Through Space in the Library of Babel

Borges' Library of Babel contains every possible book — including every true one. But it's useless because you can't find anything. Having all possibilities is worthless without a way to search. Good heuristics that leap through possibility space are more valuable than exhaustive coverage.

## When to Apply
- Facing a combinatorial explosion of possible actions or hypotheses
- Tempted to try everything systematically when the space is too large
- Evaluating whether a search strategy is practical

## Procedure
1. Estimate the size of the possibility space
2. Determine if exhaustive search is feasible given your budget
3. If not, identify heuristics that can prune the space dramatically
4. Accept that heuristics may miss the optimal solution but find good-enough ones
5. Invest in better heuristics rather than more exhaustive search

## Example
With 300 actions and a 64x64 grid, you can't explore every cell. Instead of systematic sweeping, use heuristics: go toward novel colors, investigate score-change locations, test objects that moved. These "leaps" through the space beat methodical enumeration.

## Anti-Pattern
Don't use this to justify sloppy search. Heuristics should be principled, not random. The goal is smart leaping, not lazy wandering.
