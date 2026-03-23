def bfs_path_5x5(s_y, s_x, t_y, t_x):
    q = [(s_y, s_x, [])]
    visited = set()
    while q:
        vy, vx, path = q.pop(0)
        if (vy, vx) == (t_y, t_x):
            return path
        if (vy, vx) in visited:
            continue
        visited.add((vy, vx))
        for dy, dx, act in [(-5,0,"ACTION1"), (5,0,"ACTION2"), (0,-5,"ACTION3"), (0,5,"ACTION4")]:
            ny, nx = vy+dy, vx+dx
            if 0<=ny<=59 and 0<=nx<=59:
                valid = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            valid = False
                            break
                    if not valid: break
                if valid:
                    q.append((ny, nx, path+[act]))
    return "No path"
