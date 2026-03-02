def find_valid_path(sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = set([(sy, sx)])
    
    while queue:
        y, x, path = queue.pop(0)
        if y == ty and x == tx:
            return path
            
        for dy, dx, action in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                if (ny, nx) not in visited:
                    collision = False
                    for r in range(ny, ny + 5):
                        for c in range(nx, nx + 5):
                            # Ignore 5s inside goal (11-13, 35-37)
                            is_in_goal = (11 <= r <= 13 and 35 <= c <= 37)
                            if grids[0][r][c] == 5 and not is_in_goal:
                                collision = True
                                break
                        if collision:
                            break
                    if not collision:
                        visited.add((ny, nx))
                        queue.append((ny, nx, path + [action]))
    return None
