import statistics
from typing import List, Dict


def detect_spike(daily_counts: List[int], baseline_days: int = 7) -> Dict:
    """
    Detect if today's count is an abnormal spike.
    Spike condition: today > (mean_last_N_days + 2 × std_dev)

    Args:
        daily_counts:  list of daily counts, last value = today
        baseline_days: how many days to use for mean/std calculation
    Returns:
        dict with spike analysis details
    """
    if len(daily_counts) < 2:
        return {
            "today_count": daily_counts[-1] if daily_counts else 0,
            "mean_last_7_days": 0.0,
            "std_dev": 0.0,
            "threshold": 0.0,
            "is_spike": False,
            "reason": "not enough data"
        }

    today = daily_counts[-1]

    # Use last N days BEFORE today as baseline
    baseline = daily_counts[-(baseline_days + 1):-1] if len(daily_counts) >= baseline_days + 1 else daily_counts[:-1]

    mean   = statistics.mean(baseline) if baseline else 0.0
    std_dev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
    threshold = mean + (2 * std_dev)
    is_spike  = today > threshold

    return {
        "today_count":      today,
        "mean_last_7_days": round(mean, 2),      # field name kept for serializer compat
        "std_dev":          round(std_dev, 2),
        "threshold":        round(threshold, 2),
        "is_spike":         is_spike
    }


def get_seasonal_weight(season: str, current_month: int) -> float:
    season_months = {
        "Summer":  [3, 4, 5, 6],
        "Monsoon": [7, 8, 9, 10],
        "Winter":  [11, 12, 1, 2],
    }
    in_season_months = season_months.get(season, [])
    return 1.5 if current_month in in_season_months else 1.0
