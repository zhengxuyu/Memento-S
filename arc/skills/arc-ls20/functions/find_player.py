def find_player(grid):
    # Player is top 2 rows 12, bottom 3 rows 9. Let's find top-left of 12.
    for y in range(len(grid) - 4):
        for x in range(len(grid[0]) - 4):
            if grid[y][x] == 12:
                # Check for 5x5 block
                is_player = True
                for ry in range(2):
                    for rx in range(5):
                        if grid[y + ry][x + rx] != 12:
                            is_player = False
                            break
                    if not is_player: break
                if is_player:
                    for ry in range(2, 5):
                        for rx in range(5):
                            if grid[y + ry][x + rx] != 9:
                                is_player = False
                                break
                        if not is_player: break
                if is_player:
                    return y, x
    return None
