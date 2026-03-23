def can_move_5x5(r, c, dr, dc, g):
    nr, nc = r + dr*5, c + dc*5
    if not (0 <= nr <= 59 and 0 <= nc <= 59): return False
    # Check 5x5 area for obstacles (color 4 and 5)
    for ir in range(5):
        for ic in range(5):
            if g[nr+ir][nc+ic] in (4, 5):
                return False
    return True
