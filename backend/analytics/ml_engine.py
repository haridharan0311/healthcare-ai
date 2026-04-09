from typing import List


def moving_average_forecast(daily_counts: List[int]) -> float:
    """
    Forecast next-day cases using weighted moving average.
    Formula: (last_3_days_avg × 0.6) + (last_7_days_avg × 0.4)

    Args:
        daily_counts: list of daily case counts, oldest → newest
                      needs at least 7 values
    Returns:
        forecasted case count (float)
    """
    if not daily_counts:
        return 0.0

    last_7 = daily_counts[-7:] if len(daily_counts) >= 7 else daily_counts
    last_3 = daily_counts[-3:] if len(daily_counts) >= 3 else daily_counts

    avg_7 = sum(last_7) / len(last_7)
    avg_3 = sum(last_3) / len(last_3)

    forecast = (avg_3 * 0.6) + (avg_7 * 0.4)
    return round(forecast, 2)


def time_decay_weight(value: float, is_recent: bool) -> float:
    """
    Apply time decay: recent data gets 0.7 weight, older gets 0.3.

    Args:
        value: raw metric value
        is_recent: True if data is from last 7 days
    Returns:
        weighted value
    """
    weight = 0.7 if is_recent else 0.3
    return round(value * weight, 2)


def weighted_trend_score(recent_count: int, older_count: int) -> float:
    """
    Combine recent + older counts into a single trend score.
    Recent window (last 7 days) weighted at 0.7,
    older window (8–30 days) weighted at 0.3.

    Args:
        recent_count: total cases in last 7 days
        older_count:  total cases in days 8–30
    Returns:
        weighted trend score
    """
    return round((recent_count * 0.7) + (older_count * 0.3), 2)


def predict_demand(trend_score: float, forecast: float) -> float:
    """
    Predicted cases = trend score + forecast value.

    Args:
        trend_score: output of weighted_trend_score()
        forecast:    output of moving_average_forecast()
    Returns:
        predicted total demand
    """
    return round(trend_score + forecast, 2)