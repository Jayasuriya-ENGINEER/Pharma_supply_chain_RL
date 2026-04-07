def compute_score(total_reward):
    return max(0.0, min(1.0, total_reward / 5))