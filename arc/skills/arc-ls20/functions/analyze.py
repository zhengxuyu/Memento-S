def analyze(g):
    sy, sx = None, None
    for r in range(60):
        for c in range(60):
            if g[r][c] == 12:
                is_p = True
                for rr in range(5):
                    for cc in range(5):
                        if rr < 2 and g[r+rr][c+cc] != 12: is_p = False
                        if rr >= 2 and g[r+rr][c+cc] != 9: is_p = False
                if is_p:
                    sy, sx = r, c
                    return sy, sx
    return sy, sx
