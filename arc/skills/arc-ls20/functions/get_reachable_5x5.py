def get_reachable_5x5(sy, sx, g):
    queue = [(sy, sx)]
    visited = set([(sy, sx)])
    paths = { (sy,sx): [] }
    while queue:
        y, x = queue.pop(0)
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny = y + dy
            nx = x + dx
            if ny >= 0 and ny <= 59 and nx >= 0 and nx <= 59:
                valid = True
                for r in range(5):
                    for c in range(5):
                        if ny+r > 63 or nx+c > 63 or g[ny+r][nx+c] not in [0, 3, 11, 1, 9]:  
                            valid = False
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    paths[(ny, nx)] = paths[(y,x)] + [act]
                    queue.append((ny, nx))
    return paths
