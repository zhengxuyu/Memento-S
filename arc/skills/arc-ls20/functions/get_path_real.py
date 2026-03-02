def get_path_real(sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = {(sy, sx)}
    while queue:
        y, x, path = queue.pop(0)
        if y == ty and x == tx:
            return path
        
        for dy, dx, action in [(-5,0,"ACTION1"), (5,0,"ACTION2"), (0,-5,"ACTION3"), (0,5,"ACTION4")]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                blocked = False
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] == 5:
                            blocked = True
                            break
                    if blocked: break
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny,nx))
                    queue.append((ny, nx, path + [action]))
    return None
