"""Pharmacokinetics tools: ke, t1/2, Vd, Cmax, Cmin, %T>MIC, sotalol renal dosing."""

import math

from medcal.server import mcp


@mcp.tool()
def elimination_rate_constant(
    half_life_h: float,
) -> dict:
    """Purpose: Calculate elimination rate constant from half-life.
    Population: All ages (universal PK formula).
    Inputs:
      1. half_life_h (h)
    Outputs:
      1. value (h^-1)
      2. unit (str)
      3. formula_used (str)
    """
    ke = math.log(2) / half_life_h
    return {
        "value": round(ke, 6),
        "unit": "h^-1",
        "formula_used": f"ln(2) / {half_life_h}",
    }


@mcp.tool()
def elimination_half_life(
    ke_per_h: float,
) -> dict:
    """Purpose: Calculate elimination half-life from rate constant.
    Population: All ages (universal PK formula).
    Inputs:
      1. ke_per_h (h^-1)
    Outputs:
      1. value (h)
      2. unit (str)
      3. formula_used (str)
    """
    t_half = math.log(2) / ke_per_h
    return {
        "value": round(t_half, 6),
        "unit": "h",
        "formula_used": f"ln(2) / {ke_per_h}",
    }


@mcp.tool()
def volume_of_distribution(
    vd_L_per_kg: float,
    weight_kg: float,
) -> dict:
    """Purpose: Calculate total volume of distribution.
    Population: All ages. Supply drug-specific Vd (L/kg) and appropriate weight (IBW, AdjBW, or TBW depending on drug).
    Inputs:
      1. vd_L_per_kg (L/kg)
      2. weight_kg (kg)
    Outputs:
      1. value (L)
      2. unit (str)
      3. formula_used (str)
    """
    vd = vd_L_per_kg * weight_kg
    return {
        "value": round(vd, 6),
        "unit": "L",
        "formula_used": f"{vd_L_per_kg} * {weight_kg}",
    }


@mcp.tool()
def steady_state_cmax(
    dose_mg: float,
    t_inf_h: float,
    vd_L: float,
    ke_per_h: float,
    tau_h: float,
) -> dict:
    """Purpose: Calculate steady-state peak concentration (Cmax) for intermittent IV infusion.
    Population: All ages (universal one-compartment PK model).
    Inputs:
      1. dose_mg (mg)
      2. t_inf_h (h)
      3. vd_L (L)
      4. ke_per_h (h^-1)
      5. tau_h (h)
    Outputs:
      1. value (mg/L)
      2. unit (str)
      3. formula_used (str)
    """
    numerator = 1 - math.exp(-ke_per_h * t_inf_h)
    denominator = 1 - math.exp(-ke_per_h * tau_h)
    cmax = (dose_mg / (t_inf_h * vd_L * ke_per_h)) * (numerator / denominator)
    return {
        "value": round(cmax, 6),
        "unit": "mg/L",
        "formula_used": (
            f"({dose_mg} / ({t_inf_h} * {vd_L} * {ke_per_h})) * "
            f"((1 - e^(-{ke_per_h}*{t_inf_h})) / (1 - e^(-{ke_per_h}*{tau_h})))"
        ),
    }


@mcp.tool()
def steady_state_cmin(
    cmax_mg_L: float,
    ke_per_h: float,
    tau_h: float,
    t_inf_h: float,
) -> dict:
    """Purpose: Calculate steady-state trough concentration (Cmin) for intermittent IV infusion.
    Population: All ages (universal one-compartment PK model).
    Inputs:
      1. cmax_mg_L (mg/L)
      2. ke_per_h (h^-1)
      3. tau_h (h)
      4. t_inf_h (h)
    Outputs:
      1. value (mg/L)
      2. unit (str)
      3. formula_used (str)
    """
    cmin = cmax_mg_L * math.exp(-ke_per_h * (tau_h - t_inf_h))
    return {
        "value": round(cmin, 6),
        "unit": "mg/L",
        "formula_used": f"{cmax_mg_L} * e^(-{ke_per_h} * ({tau_h} - {t_inf_h}))",
    }


@mcp.tool()
def percent_time_above_mic(
    cmax_mg_L: float,
    cmin_mg_L: float,
    ke_per_h: float,
    t_inf_h: float,
    tau_h: float,
    mic_mg_L: float,
) -> dict:
    """Purpose: Calculate percent time drug concentration exceeds MIC (%T>MIC), a PK/PD target for time-dependent antibiotics.
    Population: All ages (universal PK/PD formula).
    Inputs:
      1. cmax_mg_L (mg/L)
      2. cmin_mg_L (mg/L)
      3. ke_per_h (h^-1)
      4. t_inf_h (h)
      5. tau_h (h)
      6. mic_mg_L (mg/L)
    Outputs:
      1. value (%)
      2. unit (str)
      3. formula_used (str)
    """
    if cmin_mg_L > mic_mg_L:
        pct = 100.0
        formula = f"Cmin ({cmin_mg_L}) > MIC ({mic_mg_L}), so 100%"
    else:
        t_above = t_inf_h + math.log(cmax_mg_L / mic_mg_L) / ke_per_h
        pct = (t_above / tau_h) * 100
        formula = f"({t_inf_h} + ln({cmax_mg_L}/{mic_mg_L})/{ke_per_h}) / {tau_h} * 100"

    return {
        "value": round(pct, 6),
        "unit": "%",
        "formula_used": formula,
    }


@mcp.tool()
def sotalol_renal_dosing(
    scr_value: float,
    scr_unit: str = "mg/dL",
) -> dict:
    """Purpose: Convert serum creatinine units to mg/dL (for use before Cockcroft-Gault or similar formulas).
    Population: All ages (unit conversion only).
    Inputs:
      1. scr_value (input unit)
      2. scr_unit ("mg/dL" / "umol/L" / "umol_l", default: "mg/dL")
    Outputs:
      1. value (mg/dL)
      2. unit (str)
      3. formula_used (str)
    """
    unit_lower = scr_unit.lower().replace("\u03bc", "u").replace("\u00b5", "u")
    if unit_lower in ("umol/l", "umol_l"):
        scr_mg_dl = scr_value / 88.4
        formula = f"{scr_value} / 88.4"
    else:
        scr_mg_dl = scr_value
        formula = f"{scr_value} (already mg/dL)"

    return {
        "value": round(scr_mg_dl, 6),
        "unit": "mg/dL",
        "formula_used": formula,
    }
