"""Hazard category compatibility matrix for disaster duplicate detection."""

from typing import Dict, Tuple

# Pairwise category compatibility scores (0.0 = completely incompatible/reject, 1.0 = identical)
CATEGORY_COMPATIBILITY_MATRIX: Dict[Tuple[str, str], float] = {
    # Related precipitation and flooding hazards
    ("FLOOD_WATERLOGGING", "HEAVY_RAINFALL"): 0.75,
    ("HEAVY_RAINFALL", "FLOOD_WATERLOGGING"): 0.75,
    ("CYCLONE", "HEAVY_RAINFALL"): 0.70,
    ("HEAVY_RAINFALL", "CYCLONE"): 0.70,
    ("CYCLONE", "FLOOD_WATERLOGGING"): 0.65,
    ("FLOOD_WATERLOGGING", "CYCLONE"): 0.65,
    ("HEAVY_RAINFALL", "LANDSLIDE"): 0.65,
    ("LANDSLIDE", "HEAVY_RAINFALL"): 0.65,
    ("FLOOD_WATERLOGGING", "LANDSLIDE"): 0.60,
    ("LANDSLIDE", "FLOOD_WATERLOGGING"): 0.60,
    ("THUNDERSTORM", "LIGHTNING"): 0.85,
    ("LIGHTNING", "THUNDERSTORM"): 0.85,
    ("THUNDERSTORM", "HEAVY_RAINFALL"): 0.80,
    ("HEAVY_RAINFALL", "THUNDERSTORM"): 0.80,
    ("HEATWAVE", "DROUGHT"): 0.70,
    ("DROUGHT", "HEATWAVE"): 0.70,
    # Strictly Incompatible Hazards (hard gate: 0.0)
    ("HEATWAVE", "FLOOD_WATERLOGGING"): 0.0,
    ("FLOOD_WATERLOGGING", "HEATWAVE"): 0.0,
    ("HEATWAVE", "HEAVY_RAINFALL"): 0.0,
    ("HEAVY_RAINFALL", "HEATWAVE"): 0.0,
    ("HEATWAVE", "COLDWAVE"): 0.0,
    ("COLDWAVE", "HEATWAVE"): 0.0,
    ("DROUGHT", "FLOOD_WATERLOGGING"): 0.0,
    ("FLOOD_WATERLOGGING", "DROUGHT"): 0.0,
    ("DROUGHT", "HEAVY_RAINFALL"): 0.0,
    ("HEAVY_RAINFALL", "DROUGHT"): 0.0,
    ("DROUGHT", "LIGHTNING"): 0.0,
    ("LIGHTNING", "DROUGHT"): 0.0,
    ("DROUGHT", "THUNDERSTORM"): 0.0,
    ("THUNDERSTORM", "DROUGHT"): 0.0,
    ("DROUGHT", "CYCLONE"): 0.0,
    ("CYCLONE", "DROUGHT"): 0.0,
    ("COLDWAVE", "FLOOD_WATERLOGGING"): 0.0,
    ("FLOOD_WATERLOGGING", "COLDWAVE"): 0.0,
}


def get_category_compatibility(cat_a: str, cat_b: str) -> float:
    """Calculate compatibility score between two hazard categories.

    - Exact same category: 1.00
    - Related meteorological phenomenon: 0.60 - 0.85
    - Mutually exclusive phenomenon (e.g. Heatwave vs Flood, Drought vs Storm): 0.00
    - Unspecified/Other pairing: 0.30
    """
    clean_a = str(cat_a or "").strip().upper()
    clean_b = str(cat_b or "").strip().upper()

    if not clean_a or not clean_b:
        return 0.40

    if clean_a == clean_b:
        return 1.00

    pair = (clean_a, clean_b)
    if pair in CATEGORY_COMPATIBILITY_MATRIX:
        return CATEGORY_COMPATIBILITY_MATRIX[pair]

    return 0.30
