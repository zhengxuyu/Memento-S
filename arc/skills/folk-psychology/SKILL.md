---
name: folk-psychology
description: >
  Our everyday framework of beliefs, desires, and intentions used to
  explain behavior. Use when you need to model another agent's behavior,
  understand how "common sense" explanations work, or recognize when folk
  psychological explanations are helpful vs. misleading.
---

# Folk Psychology

Folk psychology is the informal framework humans use to explain behavior: "She did X because she wanted Y and believed Z." It attributes beliefs, desires, intentions, and fears to agents. It's remarkably effective for prediction but can mislead when applied to systems that don't actually have these states.

## When to Apply
- Modeling why another agent (human, NPC, or system) behaves a certain way
- Deciding whether to attribute goals and beliefs to a system or just describe its behavior
- Recognizing when "common sense" behavioral explanations are leading you astray
- Translating between intentional descriptions and mechanical ones

## Procedure
1. Describe the behavior you're trying to explain
2. Apply folk psychology: what beliefs and desires would explain this behavior?
3. Ask: does the system actually have these beliefs/desires, or is this a useful fiction?
4. If useful fiction: keep using it for prediction, but don't rely on it for mechanism
5. If misleading: switch to a mechanical/causal explanation

## Example
NPC behavior: moves away when the player approaches. Folk psychology: "It's afraid of the player." Useful for prediction (it will flee). But mechanically, it may just have a distance-maintenance rule. If you need to trap it, the mechanical model (it moves to maximize distance) is more actionable.

## Anti-Pattern
Don't reject folk psychology entirely — it's extremely useful for quick prediction. The error is treating folk psychological explanations as literal mechanisms rather than predictive shortcuts.
