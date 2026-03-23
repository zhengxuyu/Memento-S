def path_5(sy, sx, ty, tx):
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while q:
        y, x, p = q.popleft()
        if y == ty and x == tx: return p
        for dy, dx, action in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            if (ny, nx) not in visited and is_valid_5x5(ny, nx):
                visited.add((ny, nx))
                q.append((ny, nx, p + [action]))
    return "None"
