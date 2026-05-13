"""Body metrics tools: IBW, AdjBW, PBW, BSA, Watson TBW."""

import math

from medcal.server import mcp


@mcp.tool()
def ideal_body_weight(
    sex: str,
    height_cm: float,
) -> dict:
    """Purpose: Calculate ideal body weight (Devine formula).
    Population: Adults with height >152 cm (>60 inches). Gives invalid (negative) values for shorter patients including most children; not applicable to pediatrics.
    Inputs:
      1. sex ("male" / "female" / "m" / "f")
      2. height_cm (cm)
    Outputs:
      1. value (kg)
      2. unit (str)
      3. formula_used (str)
    """
    height_in = height_cm / 2.54
    if sex.lower() in ("male", "m"):
        ibw = 50 + 2.3 * (height_in - 60)
        formula = f"50 + 2.3 * (({height_cm}/2.54) - 60)"
    else:
        ibw = 45.5 + 2.3 * (height_in - 60)
        formula = f"45.5 + 2.3 * (({height_cm}/2.54) - 60)"

    return {
        "value": round(ibw, 6),
        "unit": "kg",
        "formula_used": formula,
    }


@mcp.tool()
def adjusted_body_weight(
    ibw_kg: float,
    tbw_kg: float,
    factor: float = 0.4,
) -> dict:
    """Purpose: Calculate adjusted body weight for obese patients.
    Population: Adults. Used when actual body weight exceeds IBW by >20-30%; factor default 0.4.
    Inputs:
      1. ibw_kg (kg)
      2. tbw_kg (kg)
      3. factor (ratio, default: 0.4)
    Outputs:
      1. value (kg)
      2. unit (str)
      3. formula_used (str)
    """
    adjbw = ibw_kg + factor * (tbw_kg - ibw_kg)
    return {
        "value": round(adjbw, 6),
        "unit": "kg",
        "formula_used": f"{ibw_kg} + {factor} * ({tbw_kg} - {ibw_kg})",
    }


@mcp.tool()
def predicted_body_weight(
    sex: str,
    height_cm: float,
) -> dict:
    """Purpose: Calculate predicted body weight for ventilator tidal volume (ARDSNet).
    Population: Adults with height >152 cm. NOT applicable to children; pediatric ARDSNet uses actual body weight-based targets per separate pediatric protocols.
    Inputs:
      1. sex ("male" / "female" / "m" / "f")
      2. height_cm (cm)
    Outputs:
      1. value (kg)
      2. unit (str)
      3. formula_used (str)
    """
    if sex.lower() in ("male", "m"):
        pbw = 50 + 0.91 * (height_cm - 152.4)
        formula = f"50 + 0.91 * ({height_cm} - 152.4)"
    else:
        pbw = 45.5 + 0.91 * (height_cm - 152.4)
        formula = f"45.5 + 0.91 * ({height_cm} - 152.4)"

    return {
        "value": round(pbw, 6),
        "unit": "kg",
        "formula_used": formula,
    }


@mcp.tool()
def bsa_dubois(
    height_cm: float,
    weight_kg: float,
) -> dict:
    """Purpose: Calculate body surface area (DuBois formula).
    Population: All ages. Validated in adults; commonly used for drug dosing in both adults and children. For very young children (<10 kg) Mosteller may be preferred.
    Inputs:
      1. height_cm (cm)
      2. weight_kg (kg)
    Outputs:
      1. value (m^2)
      2. unit (str)
      3. formula_used (str)
    """
    bsa = 0.007184 * (height_cm ** 0.725) * (weight_kg ** 0.425)
    return {
        "value": round(bsa, 6),
        "unit": "m^2",
        "formula_used": f"0.007184 * {height_cm}^0.725 * {weight_kg}^0.425",
    }


@mcp.tool()
def bsa_mosteller(
    height_cm: float,
    weight_kg: float,
) -> dict:
    """Purpose: Calculate body surface area (Mosteller formula).
    Population: All ages. Simple square-root formula; widely used in adults and children including oncology and pediatrics.
    Inputs:
      1. height_cm (cm)
      2. weight_kg (kg)
    Outputs:
      1. value (m^2)
      2. unit (str)
      3. formula_used (str)
    """
    bsa = math.sqrt(height_cm * weight_kg / 3600)
    return {
        "value": round(bsa, 6),
        "unit": "m^2",
        "formula_used": f"sqrt({height_cm} * {weight_kg} / 3600)",
    }


@mcp.tool()
def watson_tbw(
    sex: str,
    age_years: float,
    height_cm: float,
    weight_kg: float,
) -> dict:
    """Purpose: Calculate total body water (Watson equation).
    Population: Adults. Watson equation validated in adults. Note: the female formula does not include age. For pediatrics, TBW is ~0.7 × weight_kg (higher fraction than adults).
    Inputs:
      1. sex ("male" / "female" / "m" / "f")
      2. age_years (years, used only for males)
      3. height_cm (cm)
      4. weight_kg (kg)
    Outputs:
      1. value (L)
      2. unit (str)
      3. formula_used (str)
    """
    if sex.lower() in ("male", "m"):
        tbw = 2.447 - 0.09516 * age_years + 0.1074 * height_cm + 0.3362 * weight_kg
        formula = f"2.447 - 0.09516*{age_years} + 0.1074*{height_cm} + 0.3362*{weight_kg}"
    else:
        tbw = -2.097 + 0.1069 * height_cm + 0.2466 * weight_kg
        formula = f"-2.097 + 0.1069*{height_cm} + 0.2466*{weight_kg}"

    return {
        "value": round(tbw, 6),
        "unit": "L",
        "formula_used": formula,
    }
