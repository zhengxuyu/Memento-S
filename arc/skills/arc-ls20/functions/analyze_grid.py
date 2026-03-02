def analyze_grid():
    # Find player (colors 12 and 9)
    player_y12_list = [(r, c) for r in range(64) for c in range(64) if grid[r][c] == 12]
    if player_y12_list:
        py = min([r for r, c in player_y12_list])
        px = min([c for r, c in player_y12_list])
        print(f"Player pos (top-left of 5x5): y={py}, x={px}")

    # Find Goal (color 9, just the 3x3 symbol usually at the top)
    goal_cells = [(r, c) for r in range(64) for c in range(64) if grid[r][c] == 9 and r < 30]
    if goal_cells:
        gy = min([r for r, c in goal_cells])
        gx = min([c for r, c in goal_cells])
        print(f"Goal pos (top-left of 3x3): y={gy}, x={gx}")

    # Find button (color 0 and 1)
    button_cells = [(r, c) for r in range(64) for c in range(64) if grid[r][c] in [0, 1]]
    if button_cells:
        cy = min([r for r, c in button_cells])
        cx = min([c for r, c in button_cells])
        print(f"Button bounding box: y={cy}-{max([r for r,c in button_cells])}, x={cx}-{max([c for r,c in button_cells])}")
    
    # Analyze the Pattern Display
    print("Pattern Display:")
    for r in range(55, 61):
        row_str = ""
        for c in range(3, 9):
            row_str += "XX" if grid[r][c] == 9 else ".."
        print(row_str)
