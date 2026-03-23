def can_move_3x3(r, c, dr, dc, g):
    nr, nc = r + dr*3, c + dc*3
    if not (0 <= nr <= 61 and 0 <= nc <= 61): return False
    for ir in range(3):
        for ic in range(3):
            if g[nr+ir][nc+ic] in (4, 5):
                return False
    return True
