---
name: algorithms
description: >
  Recognize formal procedures guaranteed to produce results. Apply when distinguishing
  rigorous step-by-step processes from heuristics, intuitions, or vague instructions.
---

# Algorithms

An algorithm is a foolproof recipe: a finite set of instructions that, if followed exactly, is guaranteed to produce the correct result in finite time. Algorithms are substrate-neutral — they work regardless of who or what executes them. This makes them powerful explanatory tools for showing how mindless processes achieve reliable outcomes.

## When to Apply
- Evaluating whether a proposed process is rigorous or hand-wavy
- Explaining how reliable behavior can emerge without understanding
- Distinguishing deterministic procedures from heuristic guesses

## Procedure
1. State the process precisely — can every step be followed without judgment calls?
2. Check: does it terminate in finite time for all valid inputs?
3. Check: does it guarantee the correct output?
4. If yes to all, it's an algorithm. If not, it may be a heuristic (still useful, but different)
5. Note that the executor needs zero understanding — only the ability to follow instructions

## Example
Long division is an algorithm: anyone who follows the steps will get the right answer, regardless of whether they understand why it works. Natural selection is also algorithmic — it reliably produces adaptation through a mindless generate-and-test loop, no foresight required.

## Anti-Pattern
Don't conflate "algorithmic" with "deterministic." Randomized algorithms exist and are still algorithms. Also, don't assume every effective process must be an algorithm — heuristics work well in practice despite lacking guarantees.
