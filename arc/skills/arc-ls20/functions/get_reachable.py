def get_reachable(sr, sc, size, step, g):
    q = deque([(sr,sc)])
    vis = {(sr,sc)}
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r + dr*step, c + dc*step
            if not(0<=nr<=64-size and 0<=nc<=64-size): continue
            blocked = False
            for ir in range(size):
                for ic in range(size):
                    if g[nr+ir][nc+ic] in (4,5): blocked = True
            if not blocked and (nr,nc) not in vis:
                vis.add((nr,nc))
                q.append((nr,nc))
    return vis
