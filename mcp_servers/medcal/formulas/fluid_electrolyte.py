"""Fluid & electrolyte tools: free water deficit, Adrogue-Madias, sodium capping."""

from medcal.server import mcp


@mcp.tool()
def free_water_deficit(
    sex: str,
    age_years: float,
    weight_kg: float,
    na_measured_mEq_L: float,
    na_target_mEq_L: float = 140.0,
) -> dict:
    """Purpose: Calculate free water deficit in hypernatremia.
    Population: Adults and elderly. TBW coefficient used: 0.6 (adult male), 0.5 (adult female), 0.5 (elderly male ≥65 years), 0.45 (elderly female ≥65 years). NOT applicable to children (pediatric TBW coefficient ~0.7 — this formula underestimates deficit in children).
    Inputs:
      1. sex ("male" / "female" / "m")
      2. age_years (years; ≥65 triggers elderly coefficients)
      3. weight_kg (kg)
      4. na_measured_mEq_L (mEq/L)
      5. na_target_mEq_L (mEq/L, default: 140.0)
    Outputs:
      1. value (L)
      2. unit (str)
      3. tbw_L (L)
      4. tbw_coefficient (ratio)
      5. formula_used (str)
    """
    if sex.lower() in ("male", "m"):
        coeff = 0.5 if age_years >= 65 else 0.6
    else:
        coeff = 0.45 if age_years >= 65 else 0.5

    tbw = coeff * weight_kg
    fwd = tbw * (na_measured_mEq_L / na_target_mEq_L - 1)

    return {
        "value": round(fwd, 6),
        "unit": "L",
        "tbw_L": round(tbw, 6),
        "tbw_coefficient": coeff,
        "formula_used": f"{coeff}*{weight_kg} * ({na_measured_mEq_L}/{na_target_mEq_L} - 1)",
    }


@mcp.tool()
def adrogue_madias(
    na_infusate_mEq_L: float,
    na_serum_mEq_L: float,
    tbw_L: float,
) -> dict:
    """Purpose: Calculate expected change in serum sodium per liter of infusate (Adrogue-Madias formula).
    Population: All ages. Supply total body water (TBW) appropriate for the patient's age; use watson_tbw for adults or weight × 0.7 for children.
    Inputs:
      1. na_infusate_mEq_L (mEq/L)
      2. na_serum_mEq_L (mEq/L)
      3. tbw_L (L)
    Outputs:
      1. value (mEq/L per L infusate)
      2. unit (str)
      3. formula_used (str)
    """
    delta = (na_infusate_mEq_L - na_serum_mEq_L) / (tbw_L + 1)
    return {
        "value": round(delta, 6),
        "unit": "mEq/L per L infusate",
        "formula_used": f"({na_infusate_mEq_L} - {na_serum_mEq_L}) / ({tbw_L} + 1)",
    }


@mcp.tool()
def sodium_capping(
    na_measured_mEq_L: float,
    lower: float = 120.0,
    upper: float = 135.0,
) -> dict:
    """Purpose: Cap sodium value within a safe therapeutic range (utility function).
    Population: All ages (universal clamp operation).
    Inputs:
      1. na_measured_mEq_L (mEq/L)
      2. lower (mEq/L, default: 120.0)
      3. upper (mEq/L, default: 135.0)
    Outputs:
      1. value (mEq/L)
      2. unit (str)
      3. was_capped (True/False)
      4. formula_used (str)
    """
    capped = max(lower, min(na_measured_mEq_L, upper))
    return {
        "value": round(capped, 6),
        "unit": "mEq/L",
        "was_capped": capped != na_measured_mEq_L,
        "formula_used": f"max({lower}, min({na_measured_mEq_L}, {upper}))",
    }
