def get_area_5_more():
    res = []
    for r in range(20, 50):
        row = ""
        for c in range(4, 14):
            row += f"{grids[1][r][c]:2d} "
        res.append(row)
    return "\n".join(res)
