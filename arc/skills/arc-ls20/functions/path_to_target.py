def path_to_target():
    q = [(25, 19, [])]
    vis = set([(25,19)])
    while q:
        y, x, p = q.pop(0)
        if y == 10 and x == 34: return p
        for dy, dx, a in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59 and (ny,nx) not in vis:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] == 5:
                            valid = False
                            break
                    if not valid: break
                if valid:
                    vis.add((ny,nx))
                    q.append((ny, nx, p+[a]))
    return "Not found"
