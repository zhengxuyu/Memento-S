def get_bfs_5x5(sy, sx):
    q = [(sy, sx)]
    visited = {(sy, sx)}
    path = {(sy, sx): None}
    while q:
        y, x = q.pop(0)
        for dy, dx in [(-5,0), (5,0), (0,-5), (0,5)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                valid = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] not in [0, 3, 11, 12, 9]:
                            # Wait, 12 and 9 might be our own avatar. 0,3,11 are WALKABLE
                            # If it's the secondary avatar, it's 0,8,9,12,14.
                            # Just check if it's not grid 4 or 5
                            if grid[r][c] in [4, 5]:
                                valid = False
                                break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    path[(ny, nx)] = (y, x)
                    q.append((ny, nx))
    return visited
