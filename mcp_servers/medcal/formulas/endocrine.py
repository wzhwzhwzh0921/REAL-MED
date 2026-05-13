"""Endocrine tools: DKA insulin transition (IV to SC)."""

from medcal.server import mcp


@mcp.tool()
def dka_insulin_tdd(
    iv_rate_U_h: float,
    safety_factor: float = 0.8,
) -> dict:
    """Purpose: Calculate subcutaneous total daily insulin dose (TDD) when transitioning from IV insulin infusion at DKA resolution.
    Population: Adults. Standard adult DKA transition protocol (safety factor 0.8 × 24 h IV need). Pediatric DKA transition to SC insulin uses weight-based protocols that differ from this adult approach.
    Inputs:
      1. iv_rate_U_h (U/h)
      2. safety_factor (ratio, default: 0.8)
    Outputs:
      1. value (U/day)
      2. unit (str)
      3. estimated_24h_iv_need (U/day)
      4. formula_used (str)
    """
    estimated_24h = iv_rate_U_h * 24
    tdd = estimated_24h * safety_factor
    return {
        "value": round(tdd, 6),
        "unit": "U/day",
        "estimated_24h_iv_need": round(estimated_24h, 6),
        "formula_used": f"{iv_rate_U_h} * 24 * {safety_factor}",
    }


@mcp.tool()
def dka_insulin_split(
    tdd_U: float,
    basal_fraction: float = 0.5,
    meals: int = 3,
) -> dict:
    """Purpose: Split total daily insulin dose (TDD) into basal and per-meal bolus doses.
    Population: Adults. Default 50/50 basal-bolus split is standard adult practice. Pediatric insulin regimens often use different ratios and are weight-based.
    Inputs:
      1. tdd_U (U)
      2. basal_fraction (ratio, default: 0.5)
      3. meals (count, default: 3)
    Outputs:
      1. value (U)
      2. unit (U)
      3. basal_U (U)
      4. bolus_per_meal_U (U)
      5. formula_used (str)
    """
    basal = tdd_U * basal_fraction
    bolus_total = tdd_U * (1 - basal_fraction)
    bolus_per_meal = bolus_total / meals

    return {
        "value": round(basal, 6),
        "unit": "U (basal/day)",
        "basal_U": round(basal, 6),
        "bolus_per_meal_U": round(bolus_per_meal, 6),
        "formula_used": f"Basal={tdd_U}*{basal_fraction}; Bolus=({tdd_U}*{1-basal_fraction})/{meals}",
    }
