def check_50_54():
    g = grids[-1]
    for r in range(50, 55):
        print(''.join(f"{g[r][c]:2d}" for c in range(54, 59)))
