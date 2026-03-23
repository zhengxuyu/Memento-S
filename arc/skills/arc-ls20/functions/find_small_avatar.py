def find_small_avatar():
    for r in range(60):
        for c in range(60):
            block = [grid[i][j] for i in range(r, r+3) for j in range(c, c+3)]
            if 0 in block or 14 in block or 8 in block:
                if len(set(block) & {0, 8, 9, 12, 14}) >= 2:
                    return (r, c)
