---
name: automating-the-elevator
description: >
  Design reliable systems by specifying all edge cases. Apply when building
  an automated process and you need to think through every possible input or state.
---

# Automating the Elevator

When elevators were first automated, designers had to anticipate every possible combination of button presses, floor requests, door states, and timing issues. This forced a shift from relying on a human operator's judgment to exhaustively specifying behavior. The lesson: automation requires making all implicit knowledge explicit.

## When to Apply
- Replacing a human-operated process with an automated one
- Designing a system that must handle edge cases without human intervention
- You realize you've been relying on "common sense" that a machine won't have

## Procedure
1. List every possible state the system can be in
2. For each state, list every possible input or event
3. Specify what the system should do for each state-input combination
4. Identify edge cases where the "obvious" answer isn't obvious to a machine
5. Test by imagining adversarial or unusual sequences of inputs

## Example
An elevator with the door open on floor 3 receives simultaneous requests for floors 1, 5, and 3. What should it do? Close the door first? Which floor gets priority? What if someone holds the door? Each scenario needs an explicit rule — the system can't just "figure it out."

## Anti-Pattern
Don't assume exhaustive specification is always possible or necessary. Some systems are better served by heuristics plus human oversight than by trying to enumerate every case.
