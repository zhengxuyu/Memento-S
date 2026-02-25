---
name: skill-acquisition
description: >
  Systematic learning framework for autonomous agents exploring unknown environments.
  Use on EVERY decision step: predict before acting, compare after, extract rules.
  Triggers: exploring unknown games, discovering mechanics, stuck with no score,
  retrying after failure, any context requiring "learning how to learn."
---

# Skill Acquisition

## Core Loop: Predict-Act-Compare

Every action must follow this cycle:

1. **Predict**: State what you expect to happen (grid change, score change, position)
2. **Act**: Execute exactly one action
3. **Compare**: What actually happened vs prediction?
4. **Extract**: If mismatch — what assumption was wrong? If match — what rule is confirmed?

Never act without a prediction. A wrong prediction teaches more than a lucky guess.

## DREAM Cycle (per episode)

**D-Diagnose** your level:
- Level 0: Don't know the rules → map actions first (try each ACTION1-6 once)
- Level 1: Know controls → explore systematically (visit distinct regions)
- Level 2: Know some rules → test hypotheses (predict + verify)
- Level 3: Can score reliably → optimize and exploit

**R-Reflect**: What evidence am I ignoring? What did I assume "obviously" works?

**E-Explore**: If stuck, jump to a distant strategy — don't micro-optimize a failing approach.

**A-Acquire**: When a discovery is confirmed (tested 2+ times), crystallize it as a new skill file via skill-creator. This is the ONLY way to persist knowledge for future agents.

**M-Meta**: Did this episode's strategy improve on the last? What transfers to other games?

## Productive Mistakes

- Make failures precise and diagnostic — test ONE variable at a time
- On failure ask: "What specific assumption was false?"
- Classify: wrong action mapping? wrong target? wrong sequence? wrong game model?

## Anti-Patterns (audit yourself)

- **Sphexishness**: Repeating the same failing sequence. If 3 attempts fail, change strategy entirely.
- **Rathering**: Solving an easier problem than the actual one. Check: does my action address the score?
- **Confirmation bias**: Ignoring evidence against your current theory. Actively seek disconfirming data.

## Skill Persistence

**Knowledge that is not saved as a skill file will be lost.** When you confirm a pattern works reliably (Level 2+), immediately create a skill via skill-creator to pass it to future agents.
