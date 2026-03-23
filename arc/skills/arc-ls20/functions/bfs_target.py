def bfs_target(grid, sy, sx, ty, tx):
    from collections import deque
    q = deque([((sy, sx), [])])
    seen = set([(sy,sx)])
    while q:
        (y,x), path = q.popleft()
        if (y,x) == (ty,tx): return path
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in [4, 5]:
                            valid = False
                if valid and (ny,nx) not in seen:
                    seen.add((ny,nx))
                    q.append(((ny,nx), path + [act]))
    return None
