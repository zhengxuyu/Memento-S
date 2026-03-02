def solve_maze():
    grid = grids[-1]
    
    # Player position (top-left of the 5x5 footprint)
    player_y, player_x = get_player_pos(grid)
    
    goal_cells = []
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == 9:
                # Disregard the display (r > 50) and player body (current pos)
                if r < 50 and not (player_y <= r < player_y + 5 and player_x <= c < player_x + 5):
                    goal_cells.append((r, c))
    
    print(f"Goal cells: {goal_cells}")
    
    # We want top-left of player footprint perfectly aligned 
    # That means top-left must be 1 row above and 1 col left of the 3x3 goal
    if len(goal_cells) > 0:
        goal_top_y = min(r for r, c in goal_cells)
        goal_left_x = min(c for r, c in goal_cells)
        target_y = goal_top_y - 1
        target_x = goal_left_x - 1
        print(f"Goal Top-Left: y={goal_top_y}, x={goal_left_x}")
        print(f"Target Player Pos: y={target_y}, x={target_x}")
        
    print(f"Current Player Pos: {(player_y, player_x)}")
