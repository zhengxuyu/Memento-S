---
name: frogs-eye
description: >
  Remember that perception is already interpretation, not raw data. Use when
  assuming you have access to unfiltered "ground truth" about a situation.
---

# What Does the Frog's Eye Tell the Frog's Brain?

Lettvin et al. (1959) showed that a frog's eye doesn't transmit a raw image — it sends pre-processed signals tuned for specific patterns (small moving dark spots = bugs). The frog's brain gets an interpretation, not data. All perception works this way: what you "see" is already filtered and structured by your perceptual apparatus.

## When to Apply
- Assuming your observations are raw, unbiased data
- Designing or evaluating an agent's perception pipeline
- Confused about why two observers see the same situation differently

## Procedure
1. Identify what you're treating as "raw observation"
2. Ask: what filtering, categorizing, or interpreting happened before this reached me?
3. Consider what information was discarded by the perceptual process
4. Consider what structure was imposed by the perceptual process
5. Factor these biases into your conclusions

## Example
An agent's grid observation isn't raw reality — it's already parsed into colors, positions, and objects. The color-coding is an interpretation layer. If two colors look similar, the agent might "see" them as the same, missing a crucial distinction that exists in the underlying data.

## Anti-Pattern
Don't conclude that because all perception is interpretation, no observation is reliable. Some interpretations are much better than others.
