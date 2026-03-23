def bfs_5(grid, sy, sx, ty, tx):
    seen = set([(sy,sx)])
    q = deque([((sy,sx), [])])
    while q:
        (y,x), path = q.popleft()
        if (y,x) == (ty,tx): return path
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<64 and 0<=nx<64:
                if is_valid_5x5(grid, ny, nx) and (ny,nx) not in seen:
                    seen.add((ny,nx))
                    q.append(((ny, nx), path + [act]))
    return None
