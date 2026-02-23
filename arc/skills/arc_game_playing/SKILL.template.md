---
name: arc_game_playing
description: "Core knowledge for playing ARC-AGI-3 grid games. Discover rules through experimentation."
---

# ARC-AGI-3 Game Playing

You are playing an **unknown** dynamic grid-based game. Nothing is told to you — discover everything through observation and experimentation.

## Game Basics

- **Grid**: One or more 64x64 matrices, cell values 0-15 (colors).
- **Actions**: RESET, ACTION1-ACTION6. Their meanings vary per game.
- **States**: PLAYING -> WIN or GAME_OVER.
- **Score**: Score increase = progress. Goal is WIN.
- **Budget**: Every action costs a turn. Don't waste moves.

## Your Loop

1. **Observe**: What changed? Did the grid change? Did score change?
2. **Hypothesize**: What do you think the game wants you to do?
3. **Act**: Call ONE action with a clear reason.
4. **Learn**: Record confirmed knowledge with `update_game_notes`.

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
