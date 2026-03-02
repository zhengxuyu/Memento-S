def get_path_now():
    # current player top-left = (30, 19)
    sy, sx = 30, 19
    ty, tx = 10, 34
    
    # bfs that moves by 5
    q = [(sy, sx, [])]
    visited = {(sy, sx)}
    while q:
        y, x, path = q.pop(0)
        if y == ty and x == tx:
            print("Found path:", path)
            return path
            
        for dy, dx, act in [(-5,0,"1"), (5,0,"2"), (0,-5,"3"), (0,5,"4")]:
            ny, nx = y+dy, x+dx
            if 0<=ny<60 and 0<=nx<60:
                # check if 5x5 area is clear of color 5
                blocked = False
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] == 5:
                            blocked = True
                            break
                    if blocked: break
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny,nx))
                    q.append((ny, nx, path+[act]))
    print("No path found.")
