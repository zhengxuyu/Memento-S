def reach_3x3(sy, sx):
    q = [(sy, sx)]
    visited = set([(sy, sx)])
    while q:
        y, x = q.pop(0)
        for dy, dx, a in [(-3,0,'1'), (3,0,'2'), (0,-3,'3'), (0,3,'4')]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=61 and 0<=nx<=61:
                blocked = False
                for r in range(ny, ny+3):
                    for c in range(nx, nx+3):
                        if grid[r][c] in [4, 5]:
                            blocked = True
                            break
                    if blocked: break
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx))
    return visited
