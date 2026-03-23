def get_p():
    q = [(45, 9, [])]
    visited = {(45, 9)}
    while q:
        y, x, path = q.pop(0)
        if y in [55,56] and x in [3,4]:
            return path
        for dy, dx, act in [(-5,0,'1'), (5,0,'2'), (0,-5,'3'), (0,5,'4')]:
            ny, nx = y+dy, x+dx
            if (ny, nx) not in visited:
                valid = True
                if ny < 0 or ny+4 >= 64 or nx < 0 or nx+4 >= 64:
                    valid = False
                else:
                    for r in range(ny, ny+5):
                        for c in range(nx, nx+5):
                            if grid[r][c] in [4,5]:
                                valid = False
                                break
                        if not valid: break
                if valid:
                    visited.add((ny,nx))
                    q.append((ny, nx, path + [act]))
    return "No path!"
