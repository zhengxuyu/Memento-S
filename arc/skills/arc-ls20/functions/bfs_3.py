def bfs_3(grid, sy, sx, ty, tx):
    seen = set([(sy,sx)])
    q = deque([((sy,sx), [])])
    moves = []
    while q:
        (y,x), path = q.popleft()
        if ty is not None and tx is not None and (y,x) == (ty,tx): return path
        moves.append((y,x))
        for dy, dx, act in [(-3,0,1), (3,0,2), (0,-3,3), (0,3,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<64 and 0<=nx<64:
                if is_valid_3x3(grid, ny, nx) and (ny,nx) not in seen:
                    seen.add((ny,nx))
                    q.append(((ny, nx), path + [act]))
    return moves
