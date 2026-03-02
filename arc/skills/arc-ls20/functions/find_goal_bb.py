def find_goal_bb(grid):
    min_y, max_y = 64, -1
    min_x, max_x = 64, -1
    for y in range(64):
        for x in range(64):
            # To distinguish goal from player, we only consider color 9
            # Wait, goal is also color 9. We need to find 3x3 color 9 that isn't player
            if grid[y][x] == 9:
                # Is it part of player?
                is_p = False
                for y_p, x_p in [find_player(grid) or (-10, -10)]:
                    if y_p <= y < y_p+5 and x_p <= x < x_p+5:
                        is_p = True
                if not is_p:
                    # also exclude the big 8x8 block of color 9 at the bottom left (55-60)
                    if not (y >= 55 and x <= 8):
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
    if min_y <= max_y:
        return min_y, min_x
    return None
