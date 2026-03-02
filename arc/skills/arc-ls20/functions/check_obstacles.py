def check_obstacles():
    grid = grids[-1]
    py, px = 30, 34
    ty, tx = 10, 34
    
    path_blocked = False
    for y in range(ty, py):
        for cy in range(y, y+5):
            for cx in range(px, px+5):
                if grid[cy][cx] not in [0, 1, 3, 4, 9, 12]:
                    print(f"Obstacle at {cy}, {cx}: {grid[cy][cx]}")
                    path_blocked = True
    if not path_blocked:
        print("Path UP is clear.")
