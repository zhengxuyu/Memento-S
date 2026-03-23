def print_goal():
    g = grids[-1]
    for r in range(54, 62):
        print(''.join(f"{g[r][c]:2d}" for c in range(2, 10)))
