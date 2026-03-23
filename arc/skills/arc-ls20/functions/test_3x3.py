def test_3x3(sy, sx, g):
    queue = [(sy, sx)]
    visited = set([(sy, sx)])
    paths = { (sy,sx): [] }
    while queue:
        y, x = queue.pop(0)
        for dy, dx, act in [(-3,0,1), (3,0,2), (0,-3,3), (0,3,4)]:
            ny = y + dy
            nx = x + dx
            if ny >= 0 and ny <= 61 and nx >= 0 and nx <= 61:
                valid = True
                for r in range(3):
                    for c in range(3):
                        if ny+r > 63 or nx+c > 63: valid = False
                        elif g[ny+r][nx+c] not in [0, 3, 11, 1]:  
                            valid = False
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    paths[(ny, nx)] = paths[(y,x)] + [act]
                    queue.append((ny, nx))
    return visited, paths
