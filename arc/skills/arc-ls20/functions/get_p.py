def get_p():
    for r in range(64):
        for c in range(64):
            if grid[r][c] == 12: return (r,c)
    return None
