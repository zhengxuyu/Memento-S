def my_path(sy, sx, ty, tx):
    q = [(sy, sx, [])]
    visited = {(sy, sx)}
    while q:
        cy, cx, path = q.pop(0)
        if cy == ty and cx == tx:
            return path
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in (4, 5):
                            valid = False
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [act]))
    return None
