def get_path_5x5(sy, sx, ty, tx):
    queue = [(sy, sx, [])]
    visited = {(sy, sx)}
    while queue:
        y, x, path = queue.pop(0)
        if y == ty and x == tx:
            return path
        for dy, dx, action in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<60 and 0<=nx<60:
                # check if 5x5 is clear of obstacles (4, 5)
                # Walkable: 0,3,9,1,12... basically not 4 and not 5
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in (4, 5):
                            valid = False
                            break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    queue.append((ny, nx, path + [action]))
    return None
