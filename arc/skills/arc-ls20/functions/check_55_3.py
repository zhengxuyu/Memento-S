def check_55_3():
    g = grids[-1]
    for r in range(55, 61):
        print(''.join(f"{g[r][c]:2d}" for c in range(3, 9)))
