import statistics
from typing import List
from .constants import (
    MA_WEIGHT_RECENT,
    MA_WEIGHT_HISTORICAL,
    EXPONENTIAL_SMOOTHING_ALPHA,
    TIME_DECAY_WEIGHT_RECENT,
    TIME_DECAY_WEIGHT_HISTORICAL,
    TREND_WEIGHT_RECENT,
    TREND_WEIGHT_HISTORICAL
)

def moving_average_forecast(daily_counts: List[int]) -> float:
    """
    Forecast next-day cases using weighted moving average.
    Formula: (last_3_days_avg * MA_WEIGHT_RECENT) + (last_7_days_avg * MA_WEIGHT_HISTORICAL)

    Args:
        daily_counts: list of daily case counts, oldest → newest
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

    forecast = (avg_3 * MA_WEIGHT_RECENT) + (avg_7 * MA_WEIGHT_HISTORICAL)
    return round(forecast, 2)


def exponential_smoothing_forecast(daily_counts: List[int], alpha: float = EXPONENTIAL_SMOOTHING_ALPHA) -> float:
    """
    Simple Exponential Smoothing (SES) for forecasting.
    Formula: S_t = alpha * y_t + (1 - alpha) * S_{t-1}

    Args:
        daily_counts: list of daily case counts
        alpha: smoothing factor (0 < alpha < 1).
    """
    if not daily_counts:
        return 0.0
    
    forecast = daily_counts[0]
    for i in range(1, len(daily_counts)):
        forecast = alpha * daily_counts[i] + (1 - alpha) * forecast
        
    return round(forecast, 2)


def time_decay_weight(value: float, is_recent: bool) -> float:
    """
    Apply time decay: recent data gets higher weight.

    Args:
        value: raw metric value
        is_recent: True if data is from last 7 days
    Returns:
        weighted value
    """
    weight = TIME_DECAY_WEIGHT_RECENT if is_recent else TIME_DECAY_WEIGHT_HISTORICAL
    return round(value * weight, 2)


def weighted_trend_score(recent_count: int, older_count: int) -> float:
    """
    Combine recent + older counts into a single trend score.

    Args:
        recent_count: total cases in last 7 days
        older_count:  total cases in days 8–30
    Returns:
        weighted trend score
    """
    return round((recent_count * TREND_WEIGHT_RECENT) + (older_count * TREND_WEIGHT_HISTORICAL), 2)


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
    
    try:
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        std_dev = statistics.stdev(values)
        return round(std_dev / mean, 3)
    except (statistics.StatisticsError, Exception):
        return 0.0