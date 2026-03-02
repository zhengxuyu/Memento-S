def get_goal():
    goal_cells = []
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 9:
                # check if part of 3x3 goal
                if y < 30: # goal is up top
                    goal_cells.append((y,x))
    return goal_cells
