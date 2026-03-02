def bfs_path(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    # We move by exactly 5.
    dirs = [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]
    while q:
        y, x, path = q.popleft()
        if (y, x) == (ty, tx):
            return path
        for dy, dx, act in dirs:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                if (ny, nx) not in visited:
                    # check if the 5x5 area is passable
                    # Passable if all cells are 3,0,1 or the area is the target or the area is currently our body
                    # wait, goal has 5s in it. Are 5s impassable? Yes. 
                    # Actually, if we just check if it contains 4 or 5:
                    blocked = False
                    for i in range(5):
                        for j in range(5):
                            c = grid[ny+i][nx+j]
                            if c in [4, 5]: # background void, wall
                                if (ny, nx) != (10, 34): # ignore target for now
                                    blocked = True
                    if not blocked:
                        visited.add((ny, nx))
                        q.append((ny, nx, path + [act]))
    return None
