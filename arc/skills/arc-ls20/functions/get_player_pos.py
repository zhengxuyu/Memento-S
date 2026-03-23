def get_player_pos(g):
    for r in range(len(g)):
        for c in range(len(g[r])):
            if g[r][c] in [12]:
                # verify 5x5
                if r+4 < len(g) and c+4 < len(g[0]):
                    if g[r][c] == 12 and g[r+1][c] == 12 and g[r+2][c] == 9:
                        return r, c
    return None
