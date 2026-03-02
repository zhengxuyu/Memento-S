def my_bfs(sy, sx, ty, tx):
    q = deque([[(sy,sx)]])
    visited = {(sy,sx)}
    while q:
        p = q.popleft()
        r, c = p[-1]
        if r == ty and c == tx:
            return p
        for dr, dc in [(-5,0), (5,0), (0,-5), (0,5)]:
            nr, nc = r+dr, c+dc
            if 0<=nr<60 and 0<=nc<60 and (nr,nc) not in visited:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[nr+i][nc+j] in (4,5) or grid[nr+i][nc+j] == 8:
                            valid = False
                            break
                    if not valid: break
                if valid:
                    visited.add((nr,nc))
                    q.append(p + [(nr,nc)])
    return None
