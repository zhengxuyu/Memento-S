def get_valid_moves(g, y, x):
    moves = []
    # 1: UP, 2: DOWN, 3: LEFT, 4: RIGHT
    for dy, dx, action in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
        ny, nx = y + dy, x + dx
        if 0 <= ny <= len(g)-5 and 0 <= nx <= len(g[0])-5:
            # check 5x5 block
            valid = True
            for r in range(ny, ny+5):
                for c in range(nx, nx+5):
                    # colors 0 and 3 are walkable, 4 and 5 are solid obstacles, 1 is walkable (button)
                    if g[r][c] not in [0, 1, 3, 4] and g[r][c] != 12 and g[r][c] != 9:
                        if g[r][c] == 5:
                            valid = False
                            break
                        # What other colors?
                        # Wait, what if it's the gate? Color 4 or 5.
                        if g[r][c] == 4 or g[r][c] == 5:
                            valid = False
                            break
                        # Let's consider 4 and 5 solid.
                if not valid: break
            if valid:
                moves.append((ny, nx, action))
    return moves
