def get_flood():
    q = [(25, 24)]
    seen = {(25, 24)}
    while q:
        y, x = q.pop(0)
        for act, dy, dx in [(1, -5, 0), (2, 5, 0), (3, 0, -5), (4, 0, 5)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<60 and 0<=nx<60:
                ok = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            ok = False
                if ok and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    q.append((ny, nx))
    return seen
