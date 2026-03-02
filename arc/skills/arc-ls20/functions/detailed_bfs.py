def detailed_bfs(sy, sx, ty, tx):
    q = [(sy, sx, [])]
    vis = set()
    while q:
        y, x, path = q.pop(0)
        if (y, x) == (ty, tx): return path
        if (y, x) in vis: continue
        vis.add((y, x))
        for dy, dx in [(-5,0), (5,0), (0,-5), (0,5)]:
            ny, nx = y+dy, x+dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        c = grid[ny+i][nx+j]
                        if c not in (0, 1, 3, 9, 11, 12, 4):  # Wait, is 4 walkable?
                            valid = False
                if valid:
                    q.append((ny, nx, path + [(ny, nx)]))
    return None
