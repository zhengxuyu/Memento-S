def bfs_5x5(sy, sx, ty, tx):
    q = [(sy, sx, [])]
    visited = set([(sy, sx)])
    while q:
        y, x, path = q.pop(0)
        if y == ty and x == tx:
            return path
        for dy, dx, a in [(-5,0,'1'), (5,0,'2'), (0,-5,'3'), (0,5,'4')]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                # check collisions
                blocked = False
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            blocked = True
                            break
                    if blocked: break
                if not blocked:
                    if (ny, nx) not in visited:
                        visited.add((ny, nx))
                        q.append((ny, nx, path+[a]))
    return None
