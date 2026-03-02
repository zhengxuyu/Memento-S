def bfs_from_30_34():
    q = [(30, 34, [])]
    visited = set([(30, 34)])
    while q:
        cy, cx, path = q.pop(0)
        if (cy, cx) == (45, 49):
            return path
        # 1: Up, 2: Down, 3: Left, 4: Right
        moves = [(cy-5, cx, 1), (cy+5, cx, 2), (cy, cx-5, 3), (cy, cx+5, 4)]
        for ny, nx, action in moves:
            if can_fit_5x5(grid, ny, nx) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [action]))
    return "No path"
