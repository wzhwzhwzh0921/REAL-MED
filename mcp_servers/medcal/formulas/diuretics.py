"""Diuretic tools: spironolactone/furosemide ratio adjustment."""

from medcal.server import mcp


@mcp.tool()
def diuretic_ratio(
    current_spiro_mg: float,
    current_furo_mg: float,
    step: int = 0,
) -> dict:
    """Purpose: Calculate stepped spironolactone/furosemide dose adjustment for hepatic ascites management (AASLD 5:2 ratio protocol).
    Population: Adults. AASLD ascites guidelines are adult-based; stepped doses are 100/40 → 200/80 → 300/120 → 400/160 mg/day. Not applicable to pediatric ascites management.
    Inputs:
      1. current_spiro_mg (mg/day)
      2. current_furo_mg (mg/day)
      3. step (count, default: 0)
    Outputs:
      1. value (ratio)
      2. unit (ratio)
      3. new_spironolactone_mg (mg)
      4. new_furosemide_mg (mg)
      5. current_ratio (ratio or "inf")
      6. at_max_dose (True/False)
      7. formula_used (str)
      8. warning (str, present if applicable)
    """
    steps_table = [
        (100, 40),
        (200, 80),
        (300, 120),
        (400, 160),
    ]

    current_ratio = current_spiro_mg / current_furo_mg if current_furo_mg > 0 else float("inf")

    # Find current step
    current_step_idx = None
    for i, (s, f) in enumerate(steps_table):
        if current_spiro_mg <= s and current_furo_mg <= f:
            current_step_idx = i
            break
    if current_step_idx is None:
        current_step_idx = len(steps_table) - 1

    new_idx = min(current_step_idx + step, len(steps_table) - 1)
    new_spiro, new_furo = steps_table[new_idx]
    new_ratio = new_spiro / new_furo

    at_max = new_idx == len(steps_table) - 1

    result = {
        "value": round(new_ratio, 6),
        "unit": "ratio (spironolactone/furosemide)",
        "new_spironolactone_mg": new_spiro,
        "new_furosemide_mg": new_furo,
        "current_ratio": round(current_ratio, 6),
        "at_max_dose": at_max,
        "formula_used": f"Step {new_idx}: spironolactone {new_spiro} mg / furosemide {new_furo} mg",
    }
    if at_max:
        result["warning"] = "At maximum doses; consider second-line therapy (midodrine, TIPS)"
    return result
