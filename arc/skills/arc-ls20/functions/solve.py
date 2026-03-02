def solve(sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = set([(sy, sx)])
    while queue:
        y, x, path = queue.pop(0)
        if y == ty and x == tx:
            return path
        for dy, dx, action in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < 60 and 0 <= nx < 60:
                if all(grid[ny+i][nx+j] in [0, 3] for i in range(5) for j in range(5)):
                    if (ny, nx) not in visited:
                        visited.add((ny, nx))
                        queue.append((ny, nx, path + [action]))
    return None
