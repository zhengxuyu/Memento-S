def quick_bfs_path(sy, sx, ty, tx):
    q = [(sy, sx, [])]
    vis = {(sy, sx)}
    while q:
        y, x, path = q.pop(0)
        if y == ty and x == tx: return path
        for dy, dx, a in [(-5,0,1),(5,0,2),(0,-5,3),(0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                valid = True
                for ir in range(5):
                    for ic in range(5):
                        if grid[ny+ir][nx+ic] in [4,5]: valid=False
                if valid and (ny,nx) not in vis:
                    vis.add((ny,nx))
                    q.append((ny, nx, path+[a]))
    return None
