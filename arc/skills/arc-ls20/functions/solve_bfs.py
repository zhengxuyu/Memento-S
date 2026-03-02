def solve_bfs(sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = set()
    while queue:
        y, x, path = queue.pop(0)
        if (y, x) == (ty, tx):
            return path
        if (y, x) in visited:
            continue
        visited.add((y, x))
        # try 4 dirs
        for dy, dx, act in [(-5,0,"Up"), (5,0,"Down"), (0,-5,"Left"), (0,5,"Right")]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                # check if target 5x5 overlaps with any color 4 or 5
                blocked = False
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in (4, 5):
                            blocked = True
                            break
                    if blocked: break
                if not blocked:
                    queue.append((ny, nx, path + [act]))
    return None
