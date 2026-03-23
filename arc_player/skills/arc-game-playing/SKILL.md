---
name: "ARC-AGI-3 Game Player Guide"
description: "How to play ARC games — discover mechanics through observation and experimentation"
---

# How To Play

You are playing an unknown game on a 64x64 grid. You don't know the rules — discover them.

## Your Tools
- **ACTION1-ACTION6**: Game actions. Their meaning is UNKNOWN — discover through experimentation.
- **Memory tools**: Save discoveries, form hypotheses, confirm/contradict with evidence.

## Scientific Method
1. **Observe**: Read the grid carefully after each action. What changed? What didn't?
2. **Record**: Write raw observations to `discoveries/` — coordinates, colors, what moved.
3. **Hypothesize**: Write theories to `hypotheses/` — what do you think each action does?
4. **Test**: Take an action specifically to test a hypothesis. Predict what will happen BEFORE acting.
5. **Update evidence**:
   - Prediction correct? → `confirm(filename, evidence)` — at 2✓, auto-promotes to verified/.
   - Prediction wrong? → `contradict(filename, evidence)` — at 2✗, auto-disproves.
   - Also works on verified rules: contradictions can demote them back to hypotheses.

## CRITICAL: The Evidence Loop
**Every 3-5 game actions, you MUST call `confirm` or `contradict` on at least one hypothesis.**
- After testing ACTION1: `confirm('action_mappings.md', 'Step 4: ACTION1 moved player from (30,25) to (25,25) — UP confirmed')`
- After a surprise: `contradict('mechanics.md', 'Step 12: expected push but object did not move')`
- **Hypotheses with 0✓ 0✗ are USELESS.** Add evidence to them or delete them.
- At 2✓, hypotheses auto-promote to verified/. At 2✗, they auto-disprove.

## Rules
- Discoveries = RAW FACTS (coordinates, colors, effects). No interpretations.
- Hypotheses = THEORIES (testable predictions). Must be confirmed or contradicted.
- Keep discoveries SHORT — just the facts. Long stream-of-consciousness goes in hypotheses.
- **Do NOT write long narratives into memory files.** Short, specific, factual entries only.

## Efficiency
- Timer decreases each step — don't waste actions.
- When confident about action mappings, batch multiple actions per turn.
- Focus on scoring. Once you understand a level, execute efficiently.
- **Actions without evidence updates are wasted learning opportunities.**
