def find_path_bfs():
    grid = grids[-1]
    sy, sx = 25, 39
    ty, tx = 45, 49
    # check standard astar_5x5 implementation exists
    path = get_path_real_current(sy, sx, ty, tx)
    print("Path to button:", path)
