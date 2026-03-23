def safe_bfs_5x5_path(sy, sx, ty, tx):
    q = collections.deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    m = {1: (-5, 0), 2: (5, 0), 3: (0, -5), 4: (0, 5)}
    while q:
        y, x, path = q.popleft()
        if y == ty and x == tx:
            return path
        for a, (dy, dx) in m.items():
            ny, nx = y+dy, x+dx
            if can_fit_5x5(grid, ny, nx) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path+[a]))
