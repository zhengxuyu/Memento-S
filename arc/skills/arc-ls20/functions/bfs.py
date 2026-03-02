def bfs(grid, sy, sx, ty, tx):
    q = collections.deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    actions = [(1, -5, 0), (2, 5, 0), (3, 0, -5), (4, 0, 5)]
    while q:
        y, x, path = q.popleft()
        if y == ty and x == tx:
            return path
        for a, dy, dx in actions:
            ny, nx = y + dy, x + dx
            if is_valid_move(grid, ny, nx):
                if (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [a]))
    return None
