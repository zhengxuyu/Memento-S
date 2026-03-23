def path_3(sy, sx, ty, tx):
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while q:
        y, x, p = q.popleft()
        if y == ty and x == tx: return p
        for dy, dx, action in [(-3, 0, 1), (3, 0, 2), (0, -3, 3), (0, 3, 4)]:
            ny, nx = y + dy, x + dx
            if (ny, nx) not in visited and is_valid_3x3(ny, nx):
                visited.add((ny, nx))
                q.append((ny, nx, p + [action]))
    return "None"
