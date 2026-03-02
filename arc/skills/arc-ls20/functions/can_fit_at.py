def can_fit_at(y, x):
    for r in range(5):
        for c in range(5):
            gr = y + r
            gc = x + c
            if gr < 0 or gr >= 64 or gc < 0 or gc >= 64:
                return False
            # Can I step on color 5 if my player block doesn't match? Wait. What is the rule?
            if grid[gr][gc] == 5:
                return False
    return True
