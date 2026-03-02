def test_sim():
    # current player at 40,39
    y, x = 40, 39
    path_btn = find_path_5(grid, y, x, 32, 21, exact=False)
    print("Path to btn:", path_btn)
    
    # Simulate reaching button
    for m in path_btn:
        if m == 'U': y -= 5
        elif m == 'D': y += 5
        elif m == 'L': x -= 5
        elif m == 'R': x += 5
    print("Pos at btn:", y, x)
    
    # Target goal at 10,34
    grid_sim = copy.deepcopy(grid)
    goal_y, goal_x = 11, 35
    for r in range(goal_y-2, goal_y+5):
        for c in range(goal_x-2, goal_x+5):
            if 0<=r<64 and 0<=c<64 and grid_sim[r][c] == 5:
                grid_sim[r][c] = 0
                
    path_goal = find_path_5(grid_sim, y, x, 10, 34, exact=True)
    print("Path to goal:", path_goal)
