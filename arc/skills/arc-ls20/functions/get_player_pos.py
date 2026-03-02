def get_player_pos(grid):
    # Player is 5x5 block, top 2 rows 12, bottom 3 rows 9.
    for r in range(60):
        for c in range(60):
            if grid[r][c] == 12 and grid[r+1][c] == 12 and grid[r+2][c] == 9:
                # verify full 5x5
                try:
                    match = True
                    for i in range(2):
                        for j in range(5):
                            if grid[r+i][c+j] != 12: match=False
                    for i in range(2, 5):
                        for j in range(5):
                            if grid[r+i][c+j] != 9: match=False
                    if match: return (r, c)
                except:
                    pass
    return None
