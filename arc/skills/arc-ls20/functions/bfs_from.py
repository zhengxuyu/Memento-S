def bfs_from(sy, sx):
    q = [(sy, sx)]
    visited = {(sy, sx): []}
    while q:
        y, x = q.pop(0)
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if is_valid(ny, nx) and (ny, nx) not in visited:
                visited[(ny, nx)] = visited[(y, x)] + [act]
                q.append((ny, nx))
    return visited
