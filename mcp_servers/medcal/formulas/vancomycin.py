"""Vancomycin dosing tools: clearance, AUC, dosing, loading."""

from medcal.server import mcp


@mcp.tool()
def vancomycin_clearance(
    crcl_mL_min: float,
) -> dict:
    """Purpose: Calculate vancomycin elimination rate constant (Ke) using Matzke equation.
    Population: Adults. Matzke equation validated in adult patients. Pediatric vancomycin PK differs significantly; use population-specific pediatric parameters for children.
    Inputs:
      1. crcl_mL_min (mL/min)
    Outputs:
      1. value (h^-1)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    ke = 0.00083 * crcl_mL_min + 0.0044
    return {
        "value": round(ke, 6),
        "unit": "h^-1",
        "formula_used": f"Ke = 0.00083 * {crcl_mL_min} + 0.0044",
        "interpretation": "Matzke vancomycin elimination rate constant; multiply by Vd to get Cl (L/h)",
    }


@mcp.tool()
def vancomycin_auc(
    dose_mg: float,
    interval_h: float,
    clearance_L_h: float,
) -> dict:
    """Purpose: Calculate vancomycin AUC24 for AUC-guided dosing.
    Population: Adults. Target AUC24/MIC 400–600 mg·h/L is based on adult MRSA guidelines (Rybak 2020). Pediatric AUC targets may differ.
    Inputs:
      1. dose_mg (mg)
      2. interval_h (h)
      3. clearance_L_h (L/h)
    Outputs:
      1. value (mg*h/L)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    daily_dose = dose_mg * (24 / interval_h)
    auc24 = daily_dose / clearance_L_h
    return {
        "value": round(auc24, 6),
        "unit": "mg*h/L",
        "formula_used": f"({dose_mg} * (24/{interval_h})) / {clearance_L_h}",
        "interpretation": "Target AUC24/MIC 400-600 for serious MRSA infections",
    }


@mcp.tool()
def vancomycin_dosing(
    target_auc: float,
    clearance_L_h: float,
    interval_h: float,
) -> dict:
    """Purpose: Calculate vancomycin maintenance dose from target AUC and clearance.
    Population: Adults. Use with adult-derived clearance estimates.
    Inputs:
      1. target_auc (mg*h/L)
      2. clearance_L_h (L/h)
      3. interval_h (h)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. daily_dose_mg (mg)
      4. formula_used (str)
    """
    daily_dose = target_auc * clearance_L_h
    interval_dose = daily_dose * (interval_h / 24)
    return {
        "value": round(interval_dose, 6),
        "unit": "mg",
        "daily_dose_mg": round(daily_dose, 6),
        "formula_used": f"{target_auc} * {clearance_L_h} * ({interval_h}/24)",
    }


@mcp.tool()
def vancomycin_loading(
    weight_kg: float,
    target_mg_per_kg: float = 25.0,
) -> dict:
    """Purpose: Calculate vancomycin loading dose (weight-based).
    Population: Adults. Standard loading dose 25–30 mg/kg actual body weight; dose is capped with a warning if >3000 mg. Pediatric loading doses follow separate institutional protocols.
    Inputs:
      1. weight_kg (kg)
      2. target_mg_per_kg (mg/kg, default: 25.0)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. formula_used (str)
      4. warning (str, present if applicable)
    """
    dose = weight_kg * target_mg_per_kg
    warning = None
    if dose > 3000:
        warning = "Loading dose >3000 mg; consider infusion rate adjustment (max 10-15 mg/min)"

    result = {
        "value": round(dose, 2),
        "unit": "mg",
        "formula_used": f"{weight_kg} * {target_mg_per_kg}",
    }
    if warning:
        result["warning"] = warning
    return result
