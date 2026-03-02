def print_p(sy, ey, sx, ex):
    for r in range(sy, ey+1):
        print(''.join(f"{grid[r][c]:2d}" for c in range(sx, ex+1)))
