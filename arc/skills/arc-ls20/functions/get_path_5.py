def get_path_5(grid, sy, sx, ty, tx):
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while q:
        cy, cx, path = q.popleft()
        if (cy, cx) == (ty, tx):
            return path
        for dy, dx, act in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = cy + dy, cx + dx
            if check_valid(grid, ny, nx) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [act]))
    return None
