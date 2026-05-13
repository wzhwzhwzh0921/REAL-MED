"""Valvular heart disease tools: Gorlin AVA/MVA, AVA index."""

import math

from medcal.server import mcp


@mcp.tool()
def gorlin_ava(
    co_L_min: float,
    sep_s: float,
    hr_bpm: float,
    delta_p_mmHg: float,
) -> dict:
    """Purpose: Calculate aortic valve area (Gorlin formula) from hemodynamic catheterization data.
    Population: Adults. Gorlin formula validated in adult acquired valvular disease. Not applied to congenital aortic valve anomalies in children where echocardiographic planimetry is preferred.
    Inputs:
      1. co_L_min (L/min)
      2. sep_s (s)
      3. hr_bpm (bpm)
      4. delta_p_mmHg (mmHg)
    Outputs:
      1. value (cm^2)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    co_mL_min = co_L_min * 1000
    ava = co_mL_min / (sep_s * hr_bpm * 44.3 * math.sqrt(delta_p_mmHg))

    if ava < 1.0:
        interp = "Severe aortic stenosis" if ava < 0.6 else "Moderate-to-severe stenosis"
    else:
        interp = "Mild stenosis or normal"

    return {
        "value": round(ava, 6),
        "unit": "cm^2",
        "formula_used": f"{co_mL_min} / ({sep_s} * {hr_bpm} * 44.3 * sqrt({delta_p_mmHg}))",
        "interpretation": interp,
    }


@mcp.tool()
def gorlin_mva(
    co_L_min: float,
    dfp_s: float,
    hr_bpm: float,
    delta_p_mmHg: float,
) -> dict:
    """Purpose: Calculate mitral valve area (Gorlin formula) from hemodynamic catheterization data.
    Population: Adults. Gorlin formula validated in adult acquired mitral stenosis. Not applicable to pediatric congenital mitral valve disease.
    Inputs:
      1. co_L_min (L/min)
      2. dfp_s (s)
      3. hr_bpm (bpm)
      4. delta_p_mmHg (mmHg)
    Outputs:
      1. value (cm^2)
      2. unit (str)
      3. formula_used (str)
    """
    co_mL_min = co_L_min * 1000
    mva = co_mL_min / (dfp_s * hr_bpm * 37.7 * math.sqrt(delta_p_mmHg))
    return {
        "value": round(mva, 6),
        "unit": "cm^2",
        "formula_used": f"{co_mL_min} / ({dfp_s} * {hr_bpm} * 37.7 * sqrt({delta_p_mmHg}))",
    }


@mcp.tool()
def ava_index(
    ava_cm2: float,
    bsa_m2: float,
) -> dict:
    """Purpose: Calculate aortic valve area index (AVAi = AVA / BSA) to account for patient body size.
    Population: Adults. Severe AS threshold <0.6 cm²/m² is an adult criterion.
    Inputs:
      1. ava_cm2 (cm^2)
      2. bsa_m2 (m^2)
    Outputs:
      1. value (cm^2/m^2)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    avai = ava_cm2 / bsa_m2
    interp = "Severe AS" if avai < 0.6 else "Non-severe"
    return {
        "value": round(avai, 6),
        "unit": "cm^2/m^2",
        "formula_used": f"{ava_cm2} / {bsa_m2}",
        "interpretation": interp,
    }
