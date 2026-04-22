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

    count_len = len(daily_counts)
    last_7 = daily_counts[-7:] if count_len >= 7 else daily_counts
    last_3 = daily_counts[-3:] if count_len >= 3 else daily_counts

    avg_7 = sum(last_7) / len(last_7)
    avg_3 = sum(last_3) / len(last_3)

    forecast = (avg_3 * 0.6) + (avg_7 * 0.4)
    return round(forecast, 2)


def exponential_smoothing_forecast(daily_counts: List[int], alpha: float = 0.3) -> float:
    """
    Simple Exponential Smoothing (SES) for forecasting.
    Formula: S_t = α * y_t + (1 - α) * S_{t-1}

    Args:
        daily_counts: list of daily case counts
        alpha: smoothing factor (0 < alpha < 1). 
               Higher alpha gives more weight to recent data.
    """
    if not daily_counts:
        return 0.0
    
    forecast = daily_counts[0]
    for i in range(1, len(daily_counts)):
        forecast = alpha * daily_counts[i] + (1 - alpha) * forecast
        
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
    """
    return round(trend_score + forecast, 2)


def calculate_volatility(values: List[float]) -> float:
    """
    Calculate Coefficient of Variation (CV) as a measure of volatility.
    CV = standard_deviation / mean
    """
    if not values or len(values) < 2:
        return 0.0
    
    import statistics
    try:
        mean = statistics.mean(values)
        if mean == 0: return 0.0
        std_dev = statistics.stdev(values)
        return round(std_dev / mean, 3)
    except:
        return 0.0