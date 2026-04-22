from typing import List, Dict

BASE_SAFETY_BUFFER = 1.2
MAX_SAFETY_BUFFER  = 1.8

def calculate_dynamic_safety_buffer(spike_count: int, total_diseases: int, volatility: float = 0.0) -> float:
    """
    FEATURE 5: Adaptive Safety Buffer.
    Adjusts restock buffer based on both spike counts AND usage volatility.
    Higher volatility or spike ratio → higher buffer.
    """
    if total_diseases == 0:
        return BASE_SAFETY_BUFFER
        
    spike_ratio = min(spike_count / total_diseases, 1.0)
    
    # Factor in volatility (0.0 to 1.0+)
    # We cap the contribution from volatility to keep buffer within reasonable bounds
    volatility_factor = min(volatility * 0.5, 0.4)
    
    base_calc = BASE_SAFETY_BUFFER + (spike_ratio * (MAX_SAFETY_BUFFER - BASE_SAFETY_BUFFER))
    final_buffer = base_calc + volatility_factor
    
    return round(min(final_buffer, MAX_SAFETY_BUFFER), 3)

def calculate_restock(
    drug_name: str,
    generic_name: str,
    predicted_demand: float,
    avg_usage: float,
    current_stock: int,
    contributing_diseases: List[str],
    safety_buffer: float = BASE_SAFETY_BUFFER,
) -> Dict:
    """
    Formula:
        expected_demand   = predicted_demand × avg_usage × safety_buffer
        suggested_restock = max(0, expected_demand - current_stock)

    avg_usage      = total_quantity / total_cases (must come from DB)
    safety_buffer  = 1.2 base, auto-adjusted up to 1.8 based on spike count
    """
    expected_demand   = round(predicted_demand * avg_usage * safety_buffer, 2)
    suggested_restock = max(0, int(expected_demand - current_stock))

    if current_stock == 0:
        status = "critical"
    elif suggested_restock == 0:
        status = "sufficient"
    else:
        shortage_pct = (
            (expected_demand - current_stock) / expected_demand * 100
            if expected_demand > 0 else 100
        )
        status = "critical" if shortage_pct > 50 else "low"

    return {
        "drug_name":             drug_name,
        "generic_name":          generic_name,
        "current_stock":         current_stock,
        "predicted_demand":      expected_demand,
        "suggested_restock":     suggested_restock,
        "contributing_diseases": contributing_diseases,
        "status":                status,
        "safety_buffer":         safety_buffer,
    }

def apply_multi_disease_contribution(disease_demands: List[Dict]) -> float:
    """
    Combined demand = Σ (disease_demand × seasonal_weight)
    No hardcoded disease mapping — fully data-driven.
    """
    return round(
        sum(d["predicted_demand"] * d.get("seasonal_weight", 1.0)
            for d in disease_demands),
        2
    )
