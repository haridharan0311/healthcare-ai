from typing import List, Dict


SAFETY_BUFFER = 1.2   # 20% extra stock above predicted demand


def calculate_restock(
    drug_name: str,
    generic_name: str,
    predicted_demand: float,
    avg_quantity_per_prescription: float,
    current_stock: int,
    contributing_diseases: List[str]
) -> Dict:
    """
    Calculate how much of a drug to restock.

    Formula:
        expected_demand = (predicted_demand × avg_quantity) × SAFETY_BUFFER
        suggested_restock = max(0, expected_demand - current_stock)

    Args:
        drug_name:                    name of the drug
        generic_name:                 generic/chemical name
        predicted_demand:             output of ml_engine.predict_demand()
        avg_quantity_per_prescription: average units prescribed per script
        current_stock:                units currently in inventory
        contributing_diseases:        list of disease names driving demand
    Returns:
        dict with full restock recommendation
    """
    expected_demand = round(predicted_demand * avg_quantity_per_prescription * SAFETY_BUFFER, 2)
    suggested_restock = max(0, int(expected_demand - current_stock))

    status = "sufficient"
    if suggested_restock > 0:
        shortage_pct = ((expected_demand - current_stock) / expected_demand) * 100
        status = "critical" if shortage_pct > 50 else "low"

    return {
        "drug_name": drug_name,
        "generic_name": generic_name,
        "current_stock": current_stock,
        "predicted_demand": expected_demand,
        "suggested_restock": suggested_restock,
        "contributing_diseases": contributing_diseases,
        "status": status           # "sufficient" | "low" | "critical"
    }


def apply_multi_disease_contribution(disease_demands: List[Dict]) -> float:
    """
    When multiple diseases contribute to demand for one drug,
    sum their weighted demands.

    Args:
        disease_demands: list of dicts, each with:
                         { "predicted_demand": float, "seasonal_weight": float }
    Returns:
        combined demand float
    """
    total = sum(
        d["predicted_demand"] * d.get("seasonal_weight", 1.0)
        for d in disease_demands
    )
    return round(total, 2)
