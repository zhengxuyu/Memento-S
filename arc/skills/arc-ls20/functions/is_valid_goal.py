    def is_valid_goal(y, x):
        if y < 0 or y > 59 or x < 0 or x > 59:
            return False
        for r in range(y, y+5):
            for c in range(x, x+5):
                # Only consider color 5 outside the goal barrier, or just ignore 5 for now 
                pass
        return True
