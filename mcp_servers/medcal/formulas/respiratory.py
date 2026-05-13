"""Respiratory tools: alveolar gas equation, A-a gradient, protective tidal volume."""

from medcal.server import mcp


@mcp.tool()
def alveolar_gas_equation(
    fio2: float,
    paco2_mmHg: float,
    patm_mmHg: float = 760.0,
    rq: float = 0.8,
) -> dict:
    """Purpose: Calculate alveolar oxygen partial pressure (PAO2) using the alveolar gas equation.
    Population: All ages (universal formula). Adjust patm_mmHg for altitude if needed.
    Inputs:
      1. fio2 (fraction or %)
      2. paco2_mmHg (mmHg)
      3. patm_mmHg (mmHg, default: 760.0)
      4. rq (ratio, default: 0.8)
    Outputs:
      1. value (mmHg)
      2. unit (str)
      3. formula_used (str)
    """
    if fio2 > 1:
        fio2 = fio2 / 100.0
    ph2o = 47.0
    pao2 = (patm_mmHg - ph2o) * fio2 - (paco2_mmHg / rq)
    return {
        "value": round(pao2, 6),
        "unit": "mmHg",
        "formula_used": f"({patm_mmHg} - 47) * {fio2} - ({paco2_mmHg} / {rq})",
    }


@mcp.tool()
def aa_gradient(
    pao2_calculated_mmHg: float,
    pao2_measured_mmHg: float,
) -> dict:
    """Purpose: Calculate alveolar-arterial oxygen gradient (A-a gradient).
    Population: All ages (universal formula). Use aa_gradient_normal to determine if result is elevated for the patient's age.
    Inputs:
      1. pao2_calculated_mmHg (mmHg)
      2. pao2_measured_mmHg (mmHg)
    Outputs:
      1. value (mmHg)
      2. unit (str)
      3. formula_used (str)
    """
    gradient = pao2_calculated_mmHg - pao2_measured_mmHg
    return {
        "value": round(gradient, 6),
        "unit": "mmHg",
        "formula_used": f"{pao2_calculated_mmHg} - {pao2_measured_mmHg}",
    }


@mcp.tool()
def aa_gradient_normal(
    age_years: float,
) -> dict:
    """Purpose: Calculate expected normal A-a gradient for a given age (formula: (age + 10) / 4).
    Population: Adults. This age-based formula is validated for adults breathing room air. Not applicable to children; pediatric normal A-a gradient is typically <10 mmHg regardless of age.
    Inputs:
      1. age_years (years)
    Outputs:
      1. value (mmHg)
      2. unit (str)
      3. formula_used (str)
    """
    normal = (age_years + 10) / 4
    return {
        "value": round(normal, 6),
        "unit": "mmHg",
        "formula_used": f"({age_years} + 10) / 4",
    }


@mcp.tool()
def protective_tidal_volume(
    pbw_kg: float,
    ml_per_kg: float = 6.0,
) -> dict:
    """Purpose: Calculate lung-protective tidal volume based on predicted body weight (ARDSNet protocol).
    Population: Adults (ARDSNet trial enrolled adults). For pediatric ARDS, use pediatric-specific lung-protective targets and provide actual body weight rather than ARDSNet PBW.
    Inputs:
      1. pbw_kg (kg)
      2. ml_per_kg (mL/kg, default: 6.0)
    Outputs:
      1. value (mL)
      2. unit (str)
      3. formula_used (str)
    """
    vt = pbw_kg * ml_per_kg
    return {
        "value": round(vt, 6),
        "unit": "mL",
        "formula_used": f"{pbw_kg} * {ml_per_kg}",
    }
