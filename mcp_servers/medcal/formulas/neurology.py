"""Neurology tools: tPA dosing, phenytoin loading/rate, aminophylline."""

from medcal.server import mcp


@mcp.tool()
def tpa_dose(
    weight_kg: float,
) -> dict:
    """Purpose: Calculate alteplase (tPA) dose for acute ischemic stroke (0.9 mg/kg, max 90 mg).
    Population: Adults (≥18 years). AHA/ASA guidelines apply to adults; tPA for pediatric stroke is off-label with different weight-based considerations and requires specialist guidance.
    Inputs:
      1. weight_kg (kg)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. total_mg (mg)
      4. bolus_mg (mg)
      5. infusion_mg (mg)
      6. waste_mg (mg)
      7. formula_used (str)
    """
    total = min(weight_kg * 0.9, 90.0)
    bolus = total * 0.10
    infusion = total * 0.90
    waste = 100 - total

    return {
        "value": round(total, 6),
        "unit": "mg",
        "total_mg": round(total, 6),
        "bolus_mg": round(bolus, 6),
        "infusion_mg": round(infusion, 6),
        "waste_mg": round(waste, 6),
        "formula_used": f"Total dose = {round(total, 2)} mg",
    }


@mcp.tool()
def phenytoin_loading(
    adjbw_kg: float,
    target_mg_per_kg: float = 18.0,
) -> dict:
    """Purpose: Calculate phenytoin loading dose (15–20 mg/kg range).
    Population: Adults primarily. Loading dose range 15–20 mg/kg applies to adults using adjusted body weight (IBW + 1.33 × excess). Children use the same mg/kg range but based on actual body weight; maximum infusion rate differs (see phenytoin_infusion_rate).
    Inputs:
      1. adjbw_kg (kg)
      2. target_mg_per_kg (mg/kg, default: 18.0)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. range_low_mg (mg)
      4. range_high_mg (mg)
      5. formula_used (str)
    """
    dose = adjbw_kg * target_mg_per_kg
    dose_low = adjbw_kg * 15
    dose_high = adjbw_kg * 20

    return {
        "value": round(dose, 6),
        "unit": "mg",
        "range_low_mg": round(dose_low, 6),
        "range_high_mg": round(dose_high, 6),
        "formula_used": f"{adjbw_kg} * {target_mg_per_kg}",
    }


@mcp.tool()
def phenytoin_infusion_rate(
    dose_mg: float,
    max_rate_mg_min: float = 50.0,
) -> dict:
    """Purpose: Calculate minimum phenytoin infusion time based on maximum rate.
    Population: Adults (max rate default 50 mg/min). For children, max infusion rate is 1–3 mg/kg/min (much lower than adult 50 mg/min); adjust max_rate_mg_min accordingly when using this tool for pediatric patients.
    Inputs:
      1. dose_mg (mg)
      2. max_rate_mg_min (mg/min, default: 50.0)
    Outputs:
      1. value (min)
      2. unit (str)
      3. formula_used (str)
    """
    time_min = dose_mg / max_rate_mg_min
    return {
        "value": round(time_min, 6),
        "unit": "min",
        "formula_used": f"{dose_mg} / {max_rate_mg_min}",
    }
