def print_block(g, sy, ey, sx, ex):
    for r in range(sy, ey):
        print("".join(str(g[r][c]).ljust(3) for c in range(sx, ex)))
