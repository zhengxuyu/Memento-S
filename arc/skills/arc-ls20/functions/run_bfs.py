def run_bfs(grid, sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = set()
    while queue:
        y, x, path = queue.pop(0)
        if (y, x) == (ty, tx):
            return path
        if (y, x) in visited: continue
        visited.add((y, x))
        
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if ny>=0 and ny<=59 and nx>=0 and nx<=59:
                valid = True
                for rr in range(5):
                    for cc in range(5):
                        if grid[ny+rr][nx+cc] not in [0, 1, 3, 9, 12]:
                            valid = False
                            break
                    if not valid: break
                if valid:
                    queue.append((ny, nx, path+[act]))
    return None
