"""Hematology tools: Nadler blood volume, plasma volume, TPE."""

from medcal.server import mcp


@mcp.tool()
def nadler_blood_volume(
    sex: str,
    height_m: float,
    weight_kg: float,
) -> dict:
    """Purpose: Calculate total blood volume (Nadler formula).
    Population: Adults. Nadler formula validated in adults. For children, blood volume is estimated as ~80 mL/kg (neonates ~85–90 mL/kg); this formula will underestimate pediatric blood volume.
    Inputs:
      1. sex ("male" / "female" / "m" / "f")
      2. height_m (m)
      3. weight_kg (kg)
    Outputs:
      1. value (L)
      2. unit (str)
      3. formula_used (str)
    """
    if sex.lower() in ("male", "m"):
        tbv = 0.3669 * (height_m ** 3) + 0.03219 * weight_kg + 0.6041
        formula = f"0.3669 * {height_m}^3 + 0.03219 * {weight_kg} + 0.6041"
    else:
        tbv = 0.3561 * (height_m ** 3) + 0.03308 * weight_kg + 0.1833
        formula = f"0.3561 * {height_m}^3 + 0.03308 * {weight_kg} + 0.1833"

    return {
        "value": round(tbv, 6),
        "unit": "L",
        "formula_used": formula,
    }


@mcp.tool()
def plasma_volume(
    tbv_L: float,
    hct_fraction: float,
) -> dict:
    """Purpose: Calculate plasma volume from total blood volume and hematocrit.
    Population: All ages (universal formula).
    Inputs:
      1. tbv_L (L)
      2. hct_fraction (fraction or %)
    Outputs:
      1. value (L)
      2. unit (str)
      3. formula_used (str)
    """
    if hct_fraction > 1:
        hct_fraction = hct_fraction / 100.0
    pv = tbv_L * (1 - hct_fraction)
    return {
        "value": round(pv, 6),
        "unit": "L",
        "formula_used": f"{tbv_L} * (1 - {hct_fraction})",
    }


@mcp.tool()
def tpe_replacement_volume(
    plasma_volume_L: float,
    tpe_multiplier: float = 1.5,
) -> dict:
    """Purpose: Calculate replacement volume for therapeutic plasma exchange (TPE).
    Population: All ages. Standard TPE is 1.0–1.5× plasma volume; high-volume TPE (tpe_multiplier ≥2.5) uses more. Same formula applies to pediatric TPE with appropriately estimated plasma volume.
    Inputs:
      1. plasma_volume_L (L)
      2. tpe_multiplier (ratio, default: 1.5)
    Outputs:
      1. value (L)
      2. unit (str)
      3. type (str)
      4. formula_used (str)
    """
    vol = plasma_volume_L * tpe_multiplier
    is_hv = tpe_multiplier >= 2.5
    return {
        "value": round(vol, 6),
        "unit": "L",
        "type": "TPE-HV (high volume)" if is_hv else "Standard TPE",
        "formula_used": f"{plasma_volume_L} * {tpe_multiplier}",
    }
