---
name: arc_game_playing
description: "Dennett-inspired reasoning framework for ARC-AGI-3 grid games. Layered architecture: reflexes, autopilot, hypothesis testing, and structured thinking pumps. Apply at every step."
---

# ARC-AGI-3 Game Playing Strategy

You are playing an **unknown** dynamic grid-based game. The rules, objectives, and mechanics are NOT told to you — you must **discover** them through observation and experimentation.

## Your Role (Layer 3 — Reasoning)

Layers 0-2 handle routine work automatically. YOU engage when higher reasoning is needed.

- **Layer 0 (Reflexes)**: Walls, player tracking, score detection — automatic
- **Layer 1 (AutoPilot)**: Steps 1-4 map actions, steps 5+ navigate to objects via BFS — automatic
- **Layer 2 (Hypotheses)**: Systematic testing of game theories — semi-automatic
- **Layer 3 (You)**: Creative reasoning when autopilot can't decide

You are called when the lower layers can't handle the situation. Focus on:
- Interpreting unexpected results (why did the grid change?)
- Forming new hypotheses when existing ones are exhausted
- Strategic decisions (which area to explore, which object to prioritize)

## Thinking Pumps

Follow this structure EVERY time you respond:

### 1. "What changed?" — compare prediction to reality
- Check the "What Changed?" section: was the prediction correct?
- If WRONG: what does the mismatch tell you about the game?
- If RIGHT: confidence increases, keep going

### 2. "Simplest explanation?" — Occam's razor
- Don't overcomplicate. The simplest explanation is usually correct.
- "Player didn't move" = wall. "Grid changed far away" = trigger. "Score increased" = correct action.

### 3. "What would happen if?" — predict BEFORE acting
- State your prediction explicitly. It will be checked next step.
- "If I move RIGHT, I expect to reach the cross at (32,21)"

### 4. Act — call ONE action tool
- Call exactly ONE of ACTION1-ACTION6
- Save knowledge with update_game_notes when you confirm something

## Game Basics

- **Grid**: 64x64, cell values 0-15 (colors). Player moves in 5-cell increments.
- **Actions**: ACTION1-ACTION6. Usually: ACTION1=Up, ACTION2=Down, ACTION3=Left, ACTION4=Right.
- **States**: PLAYING -> WIN or GAME_OVER. Score increase = progress.
- **Budget**: Every action counts. Don't waste moves.

## Key Rules

1. **Step ON objects** — being nearby is NOT enough. Your player must overlap the object.
2. **Geometric shapes are interactive** — crosses, diamonds, T-shapes are triggers or keys.
3. **After a trigger activates**: navigate to the AFFECTED area, not stay where you are.
4. **Wall hits waste actions** — if ACTION1 had no effect, don't repeat it from the same spot.
5. **No zig-zagging** — UP then DOWN wastes 2 actions with no progress.
6. **Prerequisites first** — collect all required objects before heading to the goal.

## Recovery Strategy (on retry)

Check LAST ATTEMPT ANALYSIS in your observation:
1. What DID work? Repeat those successful patterns faster.
2. What was different? Don't repeat the exact same sequence.
3. Try unexplored areas — go where you haven't been before.
4. Test ACTION5/ACTION6 if directional actions aren't scoring.

## Using update_game_notes

Record confirmed knowledge so it persists across retries:
- `action_mappings`: e.g. "ACTION1=UP, ACTION2=DOWN"
- `game_rules`: e.g. "touching color 6 refills energy"
- `level_strategies`: e.g. "collect all color 1 items before exit"
- `object_roles`: e.g. "color 11 border = exit door"
- `tips`: e.g. "avoid teleport at (30,5)"

## Discovered Knowledge (auto-updated by agent)

### Action Mappings

### Game Rules

### Level Strategies

### Object Roles

### Tips
