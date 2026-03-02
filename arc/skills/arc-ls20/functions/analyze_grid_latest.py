def analyze_grid_latest(grid):
    player_pos = None
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 12:
                player_pos = (y, x)
                break
        if player_pos: break
    
    goal_pos = None
    # find 3x3 of 9s not overlapping with player
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 9:
                if not player_pos or (y < player_pos[0] or y >= player_pos[0]+5 or x < player_pos[1] or x >= player_pos[1]+5):
                    # check if it looks like a goal
                    is_goal = True
                    for dy, dx in [(0,0), (0,1), (0,2), (1,0), (2,0), (2,2)]:
                        ny, nx = y+dy, x+dx
                        if not (0<=ny<64 and 0<=nx<64) or grid[ny][nx] != 9:
                            is_goal = False
                            break
                    if is_goal:
                        goal_pos = (y, x)
                        break
        if goal_pos: break

    button_pos = None
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 1:
                button_pos = (y, x)
                break
        if button_pos: break

    print(f"Player pos: {player_pos}")
    print(f"Goal pos: {goal_pos}")
    print(f"Button pos: {button_pos}")
