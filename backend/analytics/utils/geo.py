def _extract_district(address: str) -> str:
    """
    Extracts the district from a comma-separated address string.
    Expected format: "Street, Area, City, State, District, Pin"
    """
    if not address:
        return 'Unknown'
    parts = [p.strip() for p in address.split(',')]
    return parts[4].strip() if len(parts) >= 5 else 'Unknown'
