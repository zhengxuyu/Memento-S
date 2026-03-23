def get_valid_moves(g, sy, sx):
    moves = []
    for d, dy, dx in [('1(UP)', -5, 0), ('2(DOWN)', 5, 0), ('3(LEFT)', 0, -5), ('4(RIGHT)', 0, 5)]:
        ny, nx = sy + dy, sx + dx
        if 0 <= ny <= 59 and 0 <= nx <= 59:
            valid = True
            for i in range(5):
                for j in range(5):
                    if g[ny+i][nx+j] in (4, 5): valid = False
            if valid: moves.append((d, ny, nx))
    return moves
