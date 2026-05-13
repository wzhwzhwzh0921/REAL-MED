"""Hemodynamics tools: CaO2, CvO2, avDO2, Fick CO, SVR, DO2."""

from medcal.server import mcp


@mcp.tool()
def arterial_oxygen_content(
    hb_g_dL: float,
    sao2_fraction: float,
    pao2_mmHg: float,
) -> dict:
    """Purpose: Calculate arterial oxygen content (CaO2).
    Population: All ages (universal formula).
    Inputs:
      1. hb_g_dL (g/dL)
      2. sao2_fraction (fraction or %)
      3. pao2_mmHg (mmHg)
    Outputs:
      1. value (mL O2/dL)
      2. unit (str)
      3. formula_used (str)
    """
    # Handle if saturation given as percentage
    if sao2_fraction > 1:
        sao2_fraction = sao2_fraction / 100.0
    cao2 = (1.34 * hb_g_dL * sao2_fraction) + (0.0031 * pao2_mmHg)
    return {
        "value": round(cao2, 6),
        "unit": "mL O2/dL",
        "formula_used": f"(1.34 * {hb_g_dL} * {sao2_fraction}) + (0.0031 * {pao2_mmHg})",
    }


@mcp.tool()
def venous_oxygen_content(
    hb_g_dL: float,
    svo2_fraction: float,
    pvo2_mmHg: float,
) -> dict:
    """Purpose: Calculate mixed venous oxygen content (CvO2).
    Population: All ages (universal formula).
    Inputs:
      1. hb_g_dL (g/dL)
      2. svo2_fraction (fraction or %)
      3. pvo2_mmHg (mmHg)
    Outputs:
      1. value (mL O2/dL)
      2. unit (str)
      3. formula_used (str)
    """
    if svo2_fraction > 1:
        svo2_fraction = svo2_fraction / 100.0
    cvo2 = (1.34 * hb_g_dL * svo2_fraction) + (0.0031 * pvo2_mmHg)
    return {
        "value": round(cvo2, 6),
        "unit": "mL O2/dL",
        "formula_used": f"(1.34 * {hb_g_dL} * {svo2_fraction}) + (0.0031 * {pvo2_mmHg})",
    }


@mcp.tool()
def avdo2(
    cao2_mL_dL: float,
    cvo2_mL_dL: float,
) -> dict:
    """Purpose: Calculate arteriovenous oxygen difference (a-vDO2).
    Population: All ages (universal formula).
    Inputs:
      1. cao2_mL_dL (mL O2/dL)
      2. cvo2_mL_dL (mL O2/dL)
    Outputs:
      1. value (mL O2/dL)
      2. unit (str)
      3. formula_used (str)
    """
    diff = cao2_mL_dL - cvo2_mL_dL
    return {
        "value": round(diff, 6),
        "unit": "mL O2/dL",
        "formula_used": f"{cao2_mL_dL} - {cvo2_mL_dL}",
    }


@mcp.tool()
def fick_cardiac_output(
    vo2_mL_min: float,
    cao2_mL_dL: float,
    cvo2_mL_dL: float,
) -> dict:
    """Purpose: Calculate cardiac output using the Fick principle.
    Population: All ages. Normal range 4–8 L/min is for adults; children have lower absolute CO but similar cardiac index when indexed to BSA.
    Inputs:
      1. vo2_mL_min (mL/min)
      2. cao2_mL_dL (mL O2/dL)
      3. cvo2_mL_dL (mL O2/dL)
    Outputs:
      1. value (L/min)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    avdo2_val = cao2_mL_dL - cvo2_mL_dL
    co = vo2_mL_min / (avdo2_val * 10)

    interp = "Normal" if 4 <= co <= 8 else ("Low" if co < 4 else "High")

    return {
        "value": round(co, 6),
        "unit": "L/min",
        "formula_used": f"{vo2_mL_min} / (({cao2_mL_dL} - {cvo2_mL_dL}) * 10)",
        "interpretation": interp,
    }


@mcp.tool()
def svr_calculation(
    map_mmHg: float,
    cvp_mmHg: float,
    co_L_min: float,
    unit: str = "dynes",
) -> dict:
    """Purpose: Calculate systemic vascular resistance (SVR).
    Population: All ages (universal formula).
    Inputs:
      1. map_mmHg (mmHg)
      2. cvp_mmHg (mmHg)
      3. co_L_min (L/min)
      4. unit ("wood" / "dynes", default: "dynes")
    Outputs:
      1. value (requested unit)
      2. unit (str)
      3. formula_used (str)
    """
    svr_wood = (map_mmHg - cvp_mmHg) / co_L_min

    if unit.lower() == "wood":
        return {
            "value": round(svr_wood, 6),
            "unit": "Wood units (mmHg*min/L)",
            "formula_used": f"({map_mmHg} - {cvp_mmHg}) / {co_L_min}",
        }
    else:
        svr_dynes = svr_wood * 80
        return {
            "value": round(svr_dynes, 6),
            "unit": "dynes*s/cm^5",
            "formula_used": f"(({map_mmHg} - {cvp_mmHg}) / {co_L_min}) * 80",
        }


@mcp.tool()
def oxygen_delivery(
    co_L_min: float,
    cao2_mL_dL: float,
    bsa_m2: float = 0.0,
) -> dict:
    """Purpose: Calculate oxygen delivery (DO2) and indexed delivery (DO2I).
    Population: All ages. Provide bsa_m2 > 0 to also compute DO2I; indexed values are preferred for comparing across patient sizes (especially pediatrics).
    Inputs:
      1. co_L_min (L/min)
      2. cao2_mL_dL (mL O2/dL)
      3. bsa_m2 (m^2, default: 0.0)
    Outputs:
      1. value (mL O2/min)
      2. unit (str)
      3. formula_used (str)
      4. do2i (mL O2/min/m^2, present if applicable)
      5. do2i_unit (str, present if applicable)
    """
    do2 = co_L_min * cao2_mL_dL * 10
    result = {
        "value": round(do2, 6),
        "unit": "mL O2/min",
        "formula_used": f"{co_L_min} * {cao2_mL_dL} * 10",
    }
    if bsa_m2 > 0:
        do2i = do2 / bsa_m2
        result["do2i"] = round(do2i, 6)
        result["do2i_unit"] = "mL O2/min/m^2"
    return result
