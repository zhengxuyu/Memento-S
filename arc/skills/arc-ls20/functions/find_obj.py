def find_obj(g, c):
    res = []
    for r in range(len(g)):
        for col in range(len(g[0])):
            if g[r][col] == c:
                res.append((r, col))
    return res
