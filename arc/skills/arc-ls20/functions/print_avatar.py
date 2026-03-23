def print_avatar():
    g = grids[-1]
    for r in range(10, 15):
        print(''.join(f"{g[r][c]:2d}" for c in range(49, 54)))
