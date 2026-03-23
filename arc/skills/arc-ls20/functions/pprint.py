def pprint(g, sy, ey, sx, ex):
    for r in range(sy, ey):
        print("".join(f"{g[r][c]:2d}" if g[r][c]!=3 else " ." for c in range(sx, ex)))
