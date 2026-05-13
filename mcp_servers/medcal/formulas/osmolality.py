"""Osmolality tools: serum osmolality, osmolal gap, toxic alcohol estimation, urine osm."""

from medcal.server import mcp


@mcp.tool()
def serum_osmolality(
    na_mEq_L: float,
    glucose_mg_dL: float,
    bun_mg_dL: float,
    ethanol_mg_dL: float = 0.0,
) -> dict:
    """Purpose: Calculate estimated serum osmolality (calculated osmolarity).
    Population: All ages (universal formula). Normal range 275–295 mOsm/kg applies to all ages.
    Inputs:
      1. na_mEq_L (mEq/L)
      2. glucose_mg_dL (mg/dL)
      3. bun_mg_dL (mg/dL)
      4. ethanol_mg_dL (mg/dL, default: 0.0)
    Outputs:
      1. value (mOsm/kg)
      2. unit (str)
      3. formula_used (str)
    """
    osm = 2 * na_mEq_L + glucose_mg_dL / 18 + bun_mg_dL / 2.8
    formula = f"2*{na_mEq_L} + {glucose_mg_dL}/18 + {bun_mg_dL}/2.8"
    if ethanol_mg_dL > 0:
        osm += ethanol_mg_dL / 4.6
        formula += f" + {ethanol_mg_dL}/4.6"

    return {
        "value": round(osm, 6),
        "unit": "mOsm/kg",
        "formula_used": formula,
    }


@mcp.tool()
def osmolal_gap(
    measured_osm_mOsm_kg: float,
    calculated_osm_mOsm_kg: float,
) -> dict:
    """Purpose: Calculate osmolal gap (measured − calculated osmolality) to screen for unmeasured osmoles.
    Population: All ages. Gap >10 mOsm/kg is abnormal; threshold applies across age groups.
    Inputs:
      1. measured_osm_mOsm_kg (mOsm/kg)
      2. calculated_osm_mOsm_kg (mOsm/kg)
    Outputs:
      1. value (mOsm/kg)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    gap = measured_osm_mOsm_kg - calculated_osm_mOsm_kg
    if gap > 10:
        interp = "Elevated; consider toxic alcohol ingestion, lactic acidosis, or other osmotically active substances"
    else:
        interp = "Normal range"

    return {
        "value": round(gap, 6),
        "unit": "mOsm/kg",
        "formula_used": f"{measured_osm_mOsm_kg} - {calculated_osm_mOsm_kg}",
        "interpretation": interp,
    }


@mcp.tool()
def toxic_alcohol_estimation(
    osm_gap_mOsm_kg: float,
    alcohol_type: str = "methanol",
) -> dict:
    """Purpose: Estimate toxic alcohol (methanol or ethylene glycol) serum concentration from osmolal gap.
    Population: All ages (universal formula). Useful as a rapid screen when direct measurement is unavailable.
    Inputs:
      1. osm_gap_mOsm_kg (mOsm/kg)
      2. alcohol_type ("methanol" / "meoh" / "ethylene_glycol", default: "methanol")
    Outputs:
      1. value (mg/dL)
      2. unit (str)
      3. substance (str)
      4. formula_used (str)
    """
    if alcohol_type.lower() in ("methanol", "meoh"):
        factor = 3.2
        name = "Methanol"
    else:
        factor = 6.2
        name = "Ethylene glycol"

    conc = osm_gap_mOsm_kg * factor
    return {
        "value": round(conc, 6),
        "unit": "mg/dL",
        "substance": name,
        "formula_used": f"{osm_gap_mOsm_kg} * {factor}",
    }


@mcp.tool()
def calculated_urine_osmolality(
    u_na_mEq_L: float,
    u_k_mEq_L: float,
    u_bun_mg_dL: float,
    u_glucose_mg_dL: float = 0.0,
) -> dict:
    """Purpose: Calculate estimated urine osmolality from urinary electrolytes.
    Population: All ages (universal formula).
    Inputs:
      1. u_na_mEq_L (mEq/L)
      2. u_k_mEq_L (mEq/L)
      3. u_bun_mg_dL (mg/dL)
      4. u_glucose_mg_dL (mg/dL, default: 0.0)
    Outputs:
      1. value (mOsm/kg)
      2. unit (str)
      3. formula_used (str)
    """
    osm = 2 * (u_na_mEq_L + u_k_mEq_L) + u_bun_mg_dL / 2.8 + u_glucose_mg_dL / 18
    formula = f"2*({u_na_mEq_L} + {u_k_mEq_L}) + {u_bun_mg_dL}/2.8 + {u_glucose_mg_dL}/18"
    return {
        "value": round(osm, 6),
        "unit": "mOsm/kg",
        "formula_used": formula,
    }


@mcp.tool()
def urine_osmolal_gap(
    measured_u_osm_mOsm_kg: float,
    calculated_u_osm_mOsm_kg: float,
) -> dict:
    """Purpose: Calculate urine osmolal gap to estimate urinary ammonium excretion in non-anion gap metabolic acidosis.
    Population: Adults. Interpretation thresholds (>200 = appropriate excretion, <150 = impaired) are based on adult reference values; pediatric thresholds may differ.
    Inputs:
      1. measured_u_osm_mOsm_kg (mOsm/kg)
      2. calculated_u_osm_mOsm_kg (mOsm/kg)
    Outputs:
      1. value (mOsm/kg)
      2. unit (str)
      3. estimated_nh4_mmol_L (mmol/L)
      4. formula_used (str)
      5. interpretation (str)
    """
    uog = measured_u_osm_mOsm_kg - calculated_u_osm_mOsm_kg
    nh4 = uog / 2

    if uog > 200:
        interp = "Appropriate renal NH4+ excretion (extrarenal cause of acidosis)"
    elif uog < 150:
        interp = "Impaired renal NH4+ excretion (consider renal tubular acidosis)"
    else:
        interp = "Indeterminate"

    return {
        "value": round(uog, 6),
        "unit": "mOsm/kg",
        "estimated_nh4_mmol_L": round(nh4, 6),
        "formula_used": f"{measured_u_osm_mOsm_kg} - {calculated_u_osm_mOsm_kg}",
        "interpretation": interp,
    }
