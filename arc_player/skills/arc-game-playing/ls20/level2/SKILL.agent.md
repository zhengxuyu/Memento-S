# General Skills
- Player avatar is a 5x5 block, top 2 rows color 12, bottom 3 rows color 9.
- Uses ACTION1 (UP), ACTION2 (DOWN), ACTION3 (LEFT), ACTION4 (RIGHT).
- Alignment is strictly to 5x5 grid cells.
- Navigating the map requires careful accounting of coordinates (Nav map x = grid col - 4).

# Level 2 Specific
- The level is a Button-Driven Puzzle. Pressing buttons transforms remote areas to match a target pattern to gain score. 
- Map features: P=player, B=button, G=goal, #=wall, .=open, W=gate.
- We need to find the button at (45,50) and step on it.