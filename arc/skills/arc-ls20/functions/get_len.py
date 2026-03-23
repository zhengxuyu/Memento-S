def get_len():
    print("Len grids:", len(grids))
    if len(grids) > 2:
        g = grids[-3]
        for r in range(52, 62):
            print("".join(str(g[r][c]).ljust(3) for c in range(2, 10)))
