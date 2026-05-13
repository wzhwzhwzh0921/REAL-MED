"""Nuclear medicine tools: Marinelli I-131, target absorbed dose, activity conversion."""

from medcal.server import mcp


@mcp.tool()
def marinelli_i131(
    target_dose_Gy: float,
    gland_mass_g: float,
    raiu_fraction: float,
    t_eff_days: float,
) -> dict:
    """Purpose: Calculate I-131 prescribed activity (MBq / mCi) for thyroid treatment using Marinelli dosimetry formula.
    Population: Adults primarily. I-131 thyroid therapy in children requires special radiation safety considerations and lower activity levels; institutional guidelines and pediatric nuclear medicine specialist input are required.
    Inputs:
      1. target_dose_Gy (Gy)
      2. gland_mass_g (g)
      3. raiu_fraction (fraction or %)
      4. t_eff_days (days)
    Outputs:
      1. value (MBq)
      2. unit (str)
      3. activity_mCi (mCi)
      4. formula_used (str)
    """
    if raiu_fraction > 1:
        raiu_fraction = raiu_fraction / 100.0

    activity_MBq = (target_dose_Gy * gland_mass_g) / (raiu_fraction * 1.44 * t_eff_days)
    activity_mCi = activity_MBq / 37

    return {
        "value": round(activity_MBq, 6),
        "unit": "MBq",
        "activity_mCi": round(activity_mCi, 6),
        "formula_used": f"({target_dose_Gy} * {gland_mass_g}) / ({raiu_fraction} * 1.44 * {t_eff_days})",
    }


@mcp.tool()
def target_absorbed_dose(
    treatment_goal: str,
) -> dict:
    """Purpose: Return guideline-based target absorbed dose (Gy) for a given thyroid treatment goal.
    Population: Adults. Supported goals: graves_control, graves_ablation, toxic_nodule, cancer_remnant. Pediatric thyroid cancer dosimetry follows separate protocols.
    Inputs:
      1. treatment_goal ("graves_control" / "graves_ablation" / "toxic_nodule" / "cancer_remnant")
    Outputs:
      1. value (Gy)
      2. unit (str)
      3. range (str)
      4. rationale (str)
      5. formula_used (str)
      6. warning (str, present if applicable)
    """
    goals = {
        "graves_control": {
            "dose_Gy": 150,
            "range": "150-200 Gy",
            "rationale": "Functional normalization while minimizing hypothyroidism risk",
        },
        "graves_ablation": {
            "dose_Gy": 200,
            "range": "200-300 Gy",
            "rationale": "Complete ablation for definitive control; higher hypothyroidism rate",
        },
        "toxic_nodule": {
            "dose_Gy": 300,
            "range": "300-400 Gy",
            "rationale": "Higher doses needed for autonomous nodules",
        },
        "cancer_remnant": {
            "dose_Gy": 100,
            "range": "30-150 Gy (remnant); higher for metastases",
            "rationale": "Remnant ablation post-thyroidectomy",
        },
    }

    key = treatment_goal.lower().replace(" ", "_").replace("-", "_")
    if key in goals:
        info = goals[key]
        return {
            "value": info["dose_Gy"],
            "unit": "Gy",
            "range": info["range"],
            "rationale": info["rationale"],
            "formula_used": f"Guideline-based: {treatment_goal}",
        }
    else:
        return {
            "value": 200,
            "unit": "Gy",
            "range": "150-300 Gy (general range)",
            "rationale": "Default mid-range; specify treatment goal for precise recommendation",
            "formula_used": "Default recommendation",
            "warning": f"Unrecognized goal '{treatment_goal}'; using default 200 Gy",
        }


@mcp.tool()
def activity_unit_conversion(
    value: float,
    from_unit: str,
    to_unit: str,
) -> dict:
    """Purpose: Convert radioactivity units between MBq, mCi, uCi, and GBq.
    Population: All ages (universal unit conversion).
    Inputs:
      1. value (source unit)
      2. from_unit ("MBq" / "mCi" / "uCi" / "GBq")
      3. to_unit ("MBq" / "mCi" / "uCi" / "GBq")
    Outputs:
      1. value (target unit or null)
      2. unit (str, present if applicable)
      3. formula_used (str, present if applicable)
      4. error (str, present if applicable)
      5. supported_units (list[str], present if applicable)
    """
    # Convert to MBq first
    to_mbq = {
        "mbq": 1.0,
        "mci": 37.0,
        "uci": 0.037,
        "gbq": 1000.0,
    }
    from_mbq = {
        "mbq": 1.0,
        "mci": 1 / 37.0,
        "uci": 1 / 0.037,
        "gbq": 0.001,
    }

    fu = from_unit.lower().replace("µ", "u")
    tu = to_unit.lower().replace("µ", "u")

    if fu not in to_mbq or tu not in from_mbq:
        return {
            "value": None,
            "error": f"Unsupported unit: {from_unit} or {to_unit}",
            "supported_units": ["MBq", "mCi", "uCi", "GBq"],
        }

    mbq_val = value * to_mbq[fu]
    result = mbq_val * from_mbq[tu]

    return {
        "value": round(result, 6),
        "unit": to_unit,
        "formula_used": f"{value} {from_unit} -> {round(result, 6)} {to_unit}",
    }
