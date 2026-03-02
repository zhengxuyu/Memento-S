def astar_5x5(sy, sx, ty, tx):
    q = [(0, sy, sx, [])]
    seen = set()
    while q:
        q.sort(key=lambda x: x[0] + abs(x[1]-ty) + abs(x[2]-tx))
        d, y, x, path = q.pop(0)
        if y == ty and x == tx:
            return path
        if (y, x) in seen: continue
        seen.add((y, x))
        for act, dy, dx in [(1, -5, 0), (2, 5, 0), (3, 0, -5), (4, 0, 5)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<60 and 0<=nx<60:
                # check if 5x5 is clear
                ok = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            ok = False
                if ok:
                    q.append((d+1, ny, nx, path+[act]))
    return None
