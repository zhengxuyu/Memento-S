def get_area_5():
    res = []
    for r in range(40, 50):
        row = ""
        for c in range(9, 19):
            row += f"{grids[1][r][c]:2d} "
        res.append(row)
    return "\n".join(res)
