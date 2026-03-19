import statistics
from typing import List, Dict


def detect_spike(daily_counts: List[int]) -> Dict:
    """
    Detect if today's count is an abnormal spike.
    Spike condition: today > (mean_last_7_days + 2 × std_dev)

    Args:
        daily_counts: list of daily counts, last value = today
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

    # Use up to last 7 days BEFORE today for the baseline
    baseline = daily_counts[-8:-1] if len(daily_counts) >= 8 else daily_counts[:-1]

    mean = statistics.mean(baseline)

    # std_dev needs at least 2 values; default to 0 if only 1 data point
    std_dev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0

    threshold = mean + (2 * std_dev)
    is_spike = today > threshold

    return {
        "today_count": today,
        "mean_last_7_days": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "threshold": round(threshold, 2),
        "is_spike": is_spike
    }


def get_seasonal_weight(season: str, current_month: int) -> float:
    """
    Return a multiplier based on how 'in season' a disease is right now.
    In-season diseases get boosted weight for trend scoring.

    Season mapping (India-based):
        Summer  → March–June      (months 3-6)
        Monsoon → July–October    (months 7–10)
        Winter  → November–Feb    (months 11, 12, 1, 2)
    """
    season_months = {
        "Summer":  [3, 4, 5, 6],
        "Monsoon": [7, 8, 9, 10],
        "Winter":  [11, 12, 1, 2],
    }

    in_season_months = season_months.get(season, [])
    return 1.5 if current_month in in_season_months else 1.0
