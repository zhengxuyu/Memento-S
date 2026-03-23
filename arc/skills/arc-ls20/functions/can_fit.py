    def can_fit(size, y, x):
        if y < 0 or y+size-1 > 63 or x < 0 or x+size-1 > 63: return False
        for r in range(y, y+size):
            for c in range(x, x+size):
                if g[r][c] in [4, 5]: return False
        return True
