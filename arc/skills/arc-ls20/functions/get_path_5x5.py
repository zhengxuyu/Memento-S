def get_path_5x5(g, sy, sx, ty, tx):
    q = [[(sy, sx)]]
    visited = set([(sy, sx)])
    moves = [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]
    while q:
        path = q.pop(0)
        y, x = path[-1]
        if y == ty and x == tx:
            return path
        for dy, dx, action in moves:
            ny, nx = y+dy, x+dx
            valid = True
            for r in range(ny, ny+5):
                for c in range(nx, nx+5):
                    if r<0 or r>=64 or c<0 or c>=64 or g[r][c] in [4, 5]:
                        valid = False
            if valid and (ny, nx) not in visited:
                visited.add((ny,nx))
                q.append(path + [(ny,nx)])
    return None
