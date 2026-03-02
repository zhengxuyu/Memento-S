    def is_valid(y, x, avoid_color_5=True):
        if y < 0 or y > 59 or x < 0 or x > 59:
            return False
        if avoid_color_5:
            for r in range(y, y+5):
                for c in range(x, x+5):
                    if grid2d[r][c] == 5:
                        return False
        return True
