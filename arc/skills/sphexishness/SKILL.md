---
name: sphexishness
description: >
  Detect rigid behavioral loops that masquerade as intelligence — like the Sphex wasp's fixed routine.
  Use when an agent appears competent but may just be running a fixed script.
---

# Sphexishness

The Sphex wasp drags a cricket to its burrow, inspects the burrow, then pulls the cricket in. If you move the cricket during inspection, it re-drags and re-inspects — forever. It looks purposeful but is a rigid loop with no real understanding. "Sphexish" behavior appears intelligent until you perturb it.

## When to Apply
- An agent succeeds at a task but might be running a fixed script
- Behavior looks intelligent until a small perturbation reveals rigidity
- You need to distinguish genuine adaptiveness from memorized routines

## Procedure
1. Identify the apparently intelligent behavior
2. Introduce a small, unexpected perturbation
3. Observe: does the agent adapt, or does it restart its fixed routine?
4. If it loops without adapting, the behavior is sphexish — competent-looking but brittle

## Example
An agent always navigates to the nearest colored object, picks it up, and returns to base. This looks purposeful. But move the base mid-trip, and the agent returns to the old location forever. Sphexish: the routine was hardcoded, not goal-directed.

## Anti-Pattern
Don't label all routine behavior as sphexish. Many efficient behaviors are rightly routine — sphexishness is specifically about inability to adapt when conditions change.
