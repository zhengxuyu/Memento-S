---
name: hypothesis_testing
description: "Disciplined approach to forming, testing, and updating hypotheses about game mechanics. Covers how to prioritize which objects to test first, how to verify a hypothesis, and how to abandon unproductive strategies quickly."
---

# Hypothesis Testing — Systematic Discovery

When you enter a game, you have many unknowns. Instead of wandering randomly, form **specific, testable hypotheses** and test them efficiently.

## Prioritizing What to Test First

Not all objects are equally likely to be important. Prioritize testing in this order:

### Priority 1: Cross and Diamond Shapes

Crosses (+) and diamonds are the **most common triggers** in grid games. They almost always do something when you step on them — rotate a region, open a wall, toggle a switch. **Test these BEFORE anything else.**

If the observation shows a CROSS composite or a cross-shaped object:
- Drop everything else
- Navigate directly to the center of the cross
- Step on it
- Observe what changed in the grid (especially far from your position)

### Priority 2: Isolated Small Objects

Small objects (1-5 cells) that are a different color from walls and floor are often collectibles or switches. Test these next.

### Priority 3: Objects Near Borders or Doors

Objects positioned near a bordered structure or door-like feature may be keys or activation triggers for that door.

### Priority 4: Large Structures

Large bordered rectangles, corridors, and walls are usually environment features, not interactive. Test these last (by trying to enter them).

## How to Test a Hypothesis

A good test has three parts:

1. **Hypothesis**: "Stepping on the cross at (32,21) will transform the grid."
2. **Action**: Navigate to (32,21) and step on it.
3. **Observation**: Check what changed — did the grid transform? Did a path open? Did score change?

After testing:
- **If the hypothesis was CONFIRMED**: Record it with `update_game_notes`. Plan your next action based on the discovery.
- **If the hypothesis was WRONG**: Cross it off and move to the next hypothesis. Don't repeat.

## The 2-Attempt Rule

Give each hypothesis at most **2 attempts**:

1. **First attempt**: Try to reach and interact with the target. If you can't reach it (walls), try one alternative route.
2. **Second attempt**: If you still can't reach it, the object might be inaccessible from your current position. Move on to the next hypothesis and come back later when you've found a way around.

**NEVER spend more than 5 actions trying to reach a single target.** If you can't reach it in 5 actions, the path requires solving something else first.

## Hypothesis Chaining

Discoveries lead to new hypotheses:

1. "I stepped on the cross and a region rotated" → **New hypothesis**: "The rotated region now has an opening I can walk through"
2. "I collected the blue item and score didn't change" → **New hypothesis**: "I need to collect ALL blue items before the score changes"
3. "Moving LEFT from (33,26) teleported me to (57,5)" → **New hypothesis**: "This is a portal. All 4 directions from the portal lead to different destinations."

Always follow up a discovery with its next logical test. Don't just observe a change — **go investigate what the change means**.

## When to Abandon a Strategy

Abandon and try something completely different when:

1. **5+ actions with no score change** after initial exploration
2. **Same position reached 3+ times** — you're looping
3. **All visible objects have been visited** and score is still 0 — you're missing something. Look for hidden areas, try ACTION5/ACTION6, or investigate teleportation.

When abandoning: pick the LEAST visited area of the grid and explore there. New discoveries are in places you haven't been.

## Cross-Retry Hypothesis Refinement

On each retry, your hypotheses should be DIFFERENT:

- **Retry 1**: "Maybe I need to go to the cross first"
- **Retry 2**: "The cross area is blocked. Maybe I need to find a different entrance. Let me explore the bottom-left area first."
- **Retry 3**: "What if the teleport IS the intended path? Let me explore what's available from the teleport destination."

If the same approach fails twice, the third attempt MUST try something fundamentally new.
