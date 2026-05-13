"""Renal calculation tools: CrCl, dose adjustments, CrCl strata."""

from medcal.server import mcp


@mcp.tool()
def cockcroft_gault_crcl(
    age_years: float,
    weight_kg: float,
    sex: str,
    scr_mg_dL: float,
) -> dict:
    """Purpose: Calculate creatinine clearance (Cockcroft-Gault).
    Population: Adults (≥18 years). NOT valid for children; use Schwartz formula for pediatric CrCl.
    Notes: Use actual body weight unless obese (BMI >30), in which case use IBW or AdjBW.
    Inputs:
      1. age_years (years)
      2. weight_kg (kg)
      3. sex ("male" / "female" / "m" / "f")
      4. scr_mg_dL (mg/dL)
    Outputs:
      1. value (mL/min)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    factor = 0.85 if sex.lower() in ("female", "f") else 1.0
    crcl = ((140 - age_years) * weight_kg) / (72 * scr_mg_dL) * factor

    if crcl > 120:
        interp = "Normal kidney function"
    elif crcl >= 60:
        interp = "Mild impairment"
    elif crcl >= 30:
        interp = "Moderate impairment"
    elif crcl >= 15:
        interp = "Severe impairment"
    else:
        interp = "End-stage renal disease"

    return {
        "value": round(crcl, 6),
        "unit": "mL/min",
        "formula_used": f"((140 - {age_years}) * {weight_kg}) / (72 * {scr_mg_dL}) * {factor}",
        "interpretation": interp,
    }


@mcp.tool()
def crcl_stratum(
    crcl_mL_min: float,
) -> dict:
    """Purpose: Map a creatinine clearance value to a renal dose stratum.
    Population: Adults. Stratification thresholds based on adult dosing guidelines.
    Inputs:
      1. crcl_mL_min (mL/min)
    Outputs:
      1. stratum (str)
      2. description (str)
      3. dose_factor (ratio)
      4. crcl_input (mL/min)
      5. formula_used (str)
    """
    if crcl_mL_min > 60:
        stratum = ">60"
        desc = "Normal dosing"
        dose_factor = 1.0
    elif crcl_mL_min >= 40:
        stratum = "40-60"
        desc = "Moderate reduction"
        dose_factor = 0.5
    elif crcl_mL_min >= 20:
        stratum = "20-40"
        desc = "Significant reduction"
        dose_factor = 0.25
    else:
        stratum = "<20"
        desc = "Contraindicated or extreme reduction"
        dose_factor = 0.0

    return {
        "stratum": stratum,
        "description": desc,
        "dose_factor": dose_factor,
        "crcl_input": round(crcl_mL_min, 2),
        "formula_used": "Standard CrCl stratification: >60, 40-60, 20-40, <20 mL/min",
    }


@mcp.tool()
def dose_adjustment_assessment(
    crcl_mL_min: float,
    threshold: float = 40.0,
) -> dict:
    """Purpose: Determine whether a creatinine clearance value is below a dose-adjustment threshold.
    Population: All ages (threshold comparison is universal).
    Inputs:
      1. crcl_mL_min (mL/min)
      2. threshold (mL/min, default: 40.0)
    Outputs:
      1. needs_adjustment (bool)
      2. value (0 or 1)
      3. unit (str)
      4. crcl_mL_min (mL/min)
      5. threshold (mL/min)
      6. formula_used (str)
    """
    needs = crcl_mL_min < threshold
    return {
        "needs_adjustment": needs,
        "value": 1 if needs else 0,
        "unit": "bool",
        "crcl_mL_min": round(crcl_mL_min, 2),
        "threshold": threshold,
        "formula_used": f"CrCl ({round(crcl_mL_min, 2)}) < {threshold} ? {needs}",
    }
