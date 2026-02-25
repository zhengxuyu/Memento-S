# Agent LLM Request — One Step Example

This shows the full prompt sent to the LLM for a single agent step (e.g., step 15 of level 2, retry #2).

---

## 1. SYSTEM PROMPT (role: "system")

```
# ARC-AGI-3 Game Playing

You are playing an **unknown** dynamic grid-based game. Nothing is told to you — discover everything through observation and experimentation.

## Game Basics
- **Grid**: One or more 64x64 matrices, cell values 0-15 (colors).
- **Actions**: RESET, ACTION1-ACTION6. Their meanings vary per game.
- **States**: PLAYING -> WIN or GAME_OVER.
- **Score**: Score increase = level completed. Goal is WIN (beat all levels).
- **Budget**: Every action costs a turn. Don't waste moves.

## Level Structure (CRITICAL)
- Each game has **multiple levels**. Score = levels completed.
- When you complete a level (score +1), the grid resets to a new layout for the next level.
- **IMPORTANT: Later levels INHERIT and BUILD ON the winning conditions of earlier levels.**
  The core mechanics (movement, interactions) stay the same, but the puzzle layout changes.
- Once you figure out HOW to score on level 1, apply the same strategy to later levels.
- Update your skill file after EACH level to record what worked.

## Your Loop (STRICT — follow every step)
1. **Observe**: What changed? Did the grid change? Did score change?
2. **Act**: Call ONE game action (ACTION1-ACTION6).
3. **Update skill**: Call `update_skill` to record what you learned.
Every turn alternates: game action → update_skill → game action → update_skill ...

## MANDATORY: Evolve a Skill
You MUST create and continuously update a skill file to persist your discoveries about this game.
- **Tool**: Call `update_skill` with full SKILL.md content (saved per-level for game `ls20`)
- **What to record**: action mappings, scoring rules, grid patterns, winning strategies
- **When to update**: after each discovery (score change, new pattern, failed hypothesis)
- **Format**: YAML frontmatter (name, description) + markdown body
- **Why**: Without a skill file, your knowledge dies with this episode. Future agents inherit ONLY what you write to the skill file.
This is NOT optional. Every insight you don't persist is lost forever.

## Your Evolved Skill — Level 2 (current)
---
name: "Scrolling Mechanics and Level Objects - Button Alignment Challenge"
description: "Navigate a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block. Top 2 rows are color 12, bottom 3 rows are color 9. The center of the avatar is the exact middle pixel.
- **Movement**: The avatar moves exactly 5 cells per action (its own width and height), essentially snapping to a 5x5 grid.
  - Action 1: Move UP (Y decreases by 5 cells)
  - Action 2: Move DOWN (Y increases by 5 cells)
  - Action 3: Move LEFT (X decreases by 5 cells)
  - Action 4: Move RIGHT (X increases by 5 cells)
- **Camera/Environment Scrolling**: Moving the player near the screen boundaries can cause thousands of cells to change...
- **Timer**: Color 11 acts as a timer at the bottom of the screen...
- **Button / Key**: Objects made of color 0 and 1. When the 5x5 player steps on these, they act as switches...
- **Gates / Obstacles**: Color 5 acts as impassable terrain.
- **Goal / Alignment**: A 3x3 symbol made of color 9 on the grid...
[...full SKILL.md content...]

## Level 2 Cheat Sheet (from previous levels — DO NOT lose this info)
---
name: "Button Alignment Challenge"
description: "Navigate a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---
# How To Win (step-by-step)
1. Locate the button (a structure of colors 0 and 1) and the goal (a 3x3 symbol of color 9).
2. Move the player block onto the button to unlock the path.
3. Confirm that impassable obstacles (color 5) blocking the goal have disappeared...
4. Navigate your player block efficiently towards the goal.
5. Center your 5x5 player block perfectly over the 3x3 goal...

# Controls
- Action 1: Move UP (Y decreases by 5 cells)
- Action 2: Move DOWN (Y increases by 5 cells)
- Action 3: Move LEFT (X decreases by 5 cells)
- Action 4: Move RIGHT (X increases by 5 cells)

# Key Facts
- **Player Block:** A 5x5 object (upper two rows are color 12, lower three rows are color 9).
- **Movement:** Movement occurs in strictly 5-cell jumps.
- **Timer:** The color 11 bar at the bottom depletes by 2 cells per move. Any wasted moves can lead to game over.
- **Obstacles:** Color 5 is an impassable wall. You must unlock them using the button.

## Evolved Skill — Level 1 (reference)
---
name: "Button and Gates"
description: "Game involves navigating a 5x5 block, stepping on button-like objects..."
---
# Game Mechanics
- We control a 5x5 block...
[...level1 SKILL.md content, truncated at 2000 chars...]
```

---

## 2. MESSAGE HISTORY (role: "user" / "assistant" / "tool")

The conversation alternates between observations and LLM responses. The history is kept in a sliding window (`MESSAGE_LIMIT = 10` messages). Older messages are summarized into `_history_summary` and appended to the system prompt.

### Message 1 (role: "user") — initial prompt
```
You are playing an ARC-AGI-3 grid game. Discover the rules yourself.
ALWAYS call exactly one tool: ACTION1-ACTION6, load_skill, update_skill, or run_code.
Use run_code ONLY for computation (BFS pathfinding, pattern analysis). Prefer game actions.
```

### Message 2 (role: "assistant") — forced RESET
```json
{
  "tool_calls": [{"id": "call_001", "type": "function", "function": {"name": "RESET", "arguments": "{}"}}]
}
```

### Message 3 (role: "tool") — observation after RESET
This is the `build_func_resp_prompt()` output:
```
# Thinking Tools (for current situation: retrying, exploring)
- **Rapoport's Rules**: Before criticizing, restate. Before dismissing, steelman...
- **Making Mistakes**: Errors aren't failures — they're data...
- **Three Species of Goulding**: Cognitive fallacies to avoid...
- **Sphexishness**: Detect and break out of rigid behavior loops...
- **Skill Acquisition**: Systematic learning framework...

# Game State: NOT_FINISHED | Level: 2 (score=1 levels completed)

# Attempt 3/51 — review past failures and try a DIFFERENT strategy.

# Grid 0 (compact):
64x64 grid, background=color 4
color 0: (32,21), (32,22), (33,21), (33,22), (34,21)
color 1: (31,21), (31,22), (34,22)
color 3: (56,4), (56,5), (56,6), (56,7), (57,4), (57,5), (57,6), (57,7)
color 5: 487 cells, rows 0-63, cols 0-63
color 8: (57,58), (57,59), (58,57), (58,58), (58,59), (58,60)
color 9: (12,36), (12,37), (12,38), (45,44), (45,45), (45,46), (45,47), (45,48), (46,44), (46,45), (46,46), (46,47), (46,48), (47,44), (47,45), (47,46), (47,47), (47,48)
color 11: 108 cells, rows 56-58, cols 8-56
color 12: (43,44), (43,45), (43,46), (43,47), (43,48), (44,44), (44,45), (44,46), (44,47), (44,48)

# Step 1 | Actions used: 0

# ACT NOW — call a game action (ACTION1-ACTION6). Use `run_code` ONLY when you need pathfinding/analysis. Then call `update_skill` to record what you learned.
```

### Message 4 (role: "assistant") — LLM's action + reasoning
```json
{
  "content": "I can see the player block (color 12+9) at around row 43-48, col 44-48. The button (color 0+1) is at ~row 31-34, col 21-22. The goal (color 9 3x3) is at row 12, col 36-38. I need to go to the button first, then navigate to the goal. Moving UP first.",
  "tool_calls": [{"id": "call_002", "type": "function", "function": {"name": "ACTION1", "arguments": "{}"}}]
}
```

### Message 5 (role: "tool") — observation after ACTION1 (UP)
```
# Thinking Tools (for current situation: exploring)
- **Intentional Stance**: Treat the game as having "intentions"...
- **Frog's Eye**: Perception is interpretation...

# Game State: NOT_FINISHED | Level: 2 (score=1 levels completed)

# Grid 0 (compact):
64x64 grid, background=color 4
color 9: (40,44), (40,45), (40,46), (40,47), (40,48), (41,44)...
color 12: (38,44), (38,45), (38,46), (38,47), (38,48), (39,44)...
[...updated positions...]

# Last action (ACTION1): 50 cells changed:
  (38,44): 4->12
  (38,45): 4->12
  [... player moved up 5 cells ...]
  (47,44): 9->4
  (47,45): 9->4

# Recent Actions:
  1. ACTION1 -> 50 cells changed (player moved)

# Step 2 | Actions used: 1

# ACT NOW — call a game action (ACTION1-ACTION6). Use `run_code` ONLY when you need pathfinding/analysis. Then call `update_skill` to record what you learned.
```

...and so on, alternating tool responses and assistant actions.

---

## 3. TOOLS (tool definitions)

```json
[
  {"type": "function", "function": {"name": "RESET", "description": "Start or restart a game.", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION1", "description": "Send input action (1, W, Up).", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION2", "description": "Send input action (2, S, Down).", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION3", "description": "Send input action (3, A, Left).", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION4", "description": "Send input action (4, D, Right).", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION5", "description": "Send input action (5, Enter, Spacebar).", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "ACTION6", "description": "Send complex input action (6, Click, Point).", "parameters": {"type": "object", "properties": {"x": {"type": "string", "description": "Coordinate X, Int<0,63>"}, "y": {"type": "string", "description": "Coordinate Y, Int<0,63>"}}, "required": ["x", "y"], "additionalProperties": false}, "strict": true}},
  {"type": "function", "function": {"name": "update_skill", "description": "Write/update the skill file to persist your discoveries about this game. Call this whenever you learn something new (action mappings, scoring rules, grid patterns, strategies). Content should be complete — it REPLACES the file.", "parameters": {"type": "object", "properties": {"content": {"type": "string", "description": "Full SKILL.md content (YAML frontmatter + markdown body)"}}, "required": ["content"]}}},
  {"type": "function", "function": {"name": "load_skill", "description": "Read a thinking tool's full SKILL.md procedure. The observation prompt shows short summaries — use this to get the complete content. Pass name='list' to see all available skills.", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "Skill directory name (e.g. 'jootsing'), prefix, or 'list' for all"}}, "required": ["name"]}}},
  {"type": "function", "function": {"name": "run_code", "description": "Execute Python code for grid analysis, pathfinding (BFS/DFS), or pattern detection. Pre-defined variables: `grid` (current 64x64 grid as 2D list), `grids` (all grids), `score`, `step_count`, `action_history` (list of past actions). Use ONLY when you need computation (e.g. BFS shortest path, counting cells, finding object positions). Do NOT use for simple observations you can do by reading the grid.", "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute. Use print() for output."}}, "required": ["code"]}}}
]
```

---

## 4. API CALL PARAMETERS

```json
{
  "model": "google/gemini-3.1-pro-preview",
  "messages": ["<system prompt>", "<message history as above>"],
  "tools": ["<tools as above>"],
  "tool_choice": "auto",
  "extra_body": {"provider": {"order": ["google-ai-studio"]}}
}
```

- First call uses `tool_choice: "auto"` — LLM can reason + optionally call a tool
- If LLM returns only text (no tool call), the agent parses ACTION names from text
- If parsing fails, a follow-up call uses `tool_choice: "required"` to force a tool call
- Hard timeout: 15 seconds via SIGALRM

---

## 5. FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT                                          │
│  ├── ARC game rules + level structure                   │
│  ├── Evolved Skill — Level 2 (SKILL.md)                │
│  ├── Cheat Sheet — Level 2 (SKILL.base.md)             │
│  ├── Evolved Skill — Level 1 (reference)               │
│  └── History Summary (if messages were truncated)       │
├─────────────────────────────────────────────────────────┤
│  MESSAGE HISTORY (sliding window, max ~10 messages)     │
│  ├── [user] initial prompt                              │
│  ├── [assistant] RESET tool call                        │
│  ├── [tool] observation (grid + diff + action history)  │
│  ├── [assistant] reasoning + ACTION tool call           │
│  ├── [tool] observation                                 │
│  ├── [assistant] reasoning + update_skill tool call     │
│  ├── [tool] "Skill saved for level 2 (1523 chars)"     │
│  ├── ...                                                │
│  └── [tool] << CURRENT OBSERVATION >>                   │
├─────────────────────────────────────────────────────────┤
│  TOOLS: RESET, ACTION1-6, update_skill, load_skill,    │
│         run_code                                        │
├─────────────────────────────────────────────────────────┤
│  → LLM responds: reasoning text + one tool_call         │
│  → Agent executes the tool, pushes result               │
│  → Loop continues                                       │
└─────────────────────────────────────────────────────────┘
```
