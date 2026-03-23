def get_grid_ch():
    res = ""
    for r in range(40, 55):
        for c in range(5, 15):
            res += f"{grid[r][c]:2d} "
        res += "\n"
    return res
