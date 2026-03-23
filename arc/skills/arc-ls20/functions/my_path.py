def my_path(sy, sx, ty, tx):
    q = [(sy, sx)]
    visited = {(sy, sx): []}
    while q:
        y, x = q.pop(0)
        if y == ty and x == tx:
            return visited[(y, x)]
        for dy, dx, act in [(-5,0,1),(5,0,2),(0,-5,3),(0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in [4, 5]:
                            valid = False
                            break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited[(ny, nx)] = visited[(y, x)] + [act]
                    q.append((ny, nx))
    return None
