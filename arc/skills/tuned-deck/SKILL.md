---
name: tuned-deck
description: >
  Be skeptical of demonstrations that seem to prove more than they actually do.
  Use when an impressive demo might be exploiting hidden constraints.
---

# The Tuned Deck

A "tuned deck" is a magic trick where the deck is pre-arranged so any demonstration the magician chooses to perform will work — but only those demonstrations. It looks like the magician has unlimited power over the cards, but the power is narrow and pre-set. Many impressive demos in AI and elsewhere are tuned decks.

## When to Apply
- A demonstration seems to prove extraordinary capability
- You're extrapolating from a curated set of examples to general ability
- Evaluating whether success in specific cases implies general competence

## Procedure
1. Identify the impressive demonstration
2. Ask: who chose which cases to demonstrate?
3. Consider whether the demo cases might be specially selected or arranged
4. Test on cases the demonstrator didn't choose — adversarial or random examples
5. Only attribute general capability if performance holds on unchosen cases

## Example
An agent scores well on 3 specific game levels that were used during development. Before concluding it's generally skilled, test it on levels the developers never saw. The original successes might be a tuned deck — working because those exact levels were optimized for.

## Anti-Pattern
Don't be so skeptical that you refuse to be impressed by genuine generalization. The point is to test before extrapolating, not to assume everything is rigged.
