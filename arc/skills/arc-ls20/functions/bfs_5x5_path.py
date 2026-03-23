def bfs_5x5_path(sr, sc, tr, tc, g):
    from collections import deque
    q = deque([(sr, sc, [])])
    visited = {(sr, sc)}
    dirs = [(-1,0,1), (1,0,2), (0,-1,3), (0,1,4)]
    while q:
        r, c, path = q.popleft()
        if (r, c) == (tr, tc): return path
        for dr, dc, a in dirs:
            nr, nc = r + dr*5, c + dc*5
            if can_move_5x5(r, c, dr, dc, g) and (nr, nc) not in visited:
                visited.add((nr, nc))
                q.append((nr, nc, path + [a]))
    return []
