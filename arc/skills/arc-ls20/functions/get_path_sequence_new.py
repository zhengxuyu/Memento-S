def get_path_sequence_new(sy, sx, ty, tx):
    q = collections.deque([(sy, sx, [])])
    visited = {(sy, sx)}
    while q:
        y, x, path = q.popleft()
        if y == ty and x == tx:
            return path
        for ny, nx, action in get_valid_moves(grid, y, x):
            if (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [action]))
    return []
