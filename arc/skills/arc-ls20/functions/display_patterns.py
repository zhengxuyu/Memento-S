def display_patterns():
    # Find goal shape
    goal_cells = []
    for r in range(64):
        for c in range(64):
            if grid[r][c] == 9 and check_grid_5x5(r-1, c-1):
                # Is it the goal? The goal is surrounded by walls initially.
                # Actually, goal is at 11,35
                pass
    
    # Just hardcode the area for goal
    print("Goal Pattern:")
    for r in range(11, 14):
        row = ""
        for c in range(35, 38):
            row += "X" if grid[r][c] == 9 else "."
        print(row)
        
    print("Display Pattern:")
    for r in range(55, 61):
        row = ""
        for c in range(3, 9):
            row += "O" if grid[r][c] == 9 else "."
        print(row)
