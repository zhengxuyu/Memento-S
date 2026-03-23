def bfs_robust(sy, sx, ty, tx, g):
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while q:
        y, x, path = q.popleft()
        if (y, x) == (ty, tx): return path
        for ny, nx, act in get_neighbors(y, x, g):
            if (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [act]))
    return None
