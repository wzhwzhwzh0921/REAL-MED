"""Burn management tools: Parkland formula, Holliday-Segar, fluid timing/rates."""

from medcal.server import mcp


@mcp.tool()
def parkland_formula(
    weight_kg: float,
    tbsa_pct: float,
    dose_mL_per_kg_pct: float = 4.0,
) -> dict:
    """Purpose: Calculate 24-hour burn resuscitation fluid volume (Parkland formula: 4 mL/kg/% TBSA).
    Population: Adults. Standard adult burn resuscitation formula. For children, modified Parkland (3 mL/kg/% TBSA) or Galveston formula (5000 mL/m² TBSA burned + 2000 mL/m² BSA/day) is preferred; also add maintenance fluid using holliday_segar for pediatric patients.
    Inputs:
      1. weight_kg (kg)
      2. tbsa_pct (%)
      3. dose_mL_per_kg_pct (mL/kg/%, default: 4.0)
    Outputs:
      1. value (mL)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    total = dose_mL_per_kg_pct * weight_kg * tbsa_pct
    return {
        "value": round(total, 6),
        "unit": "mL",
        "formula_used": f"{dose_mL_per_kg_pct} * {weight_kg} * {tbsa_pct}",
        "interpretation": "Half given in first 8h, remainder over next 16h",
    }


@mcp.tool()
def holliday_segar(
    weight_kg: float,
) -> dict:
    """Purpose: Calculate daily and hourly maintenance fluid requirements using the Holliday-Segar 4-2-1 rule.
    Population: All ages. Originally derived from pediatric data; widely applied to adults as well. Formula: 100 mL/kg/day for first 10 kg, 50 mL/kg/day for next 10 kg, 20 mL/kg/day for remaining weight.
    Inputs:
      1. weight_kg (kg)
    Outputs:
      1. value (mL/day)
      2. unit (str)
      3. hourly_rate (mL/h)
      4. hourly_unit (str)
      5. formula_used (str)
    """
    if weight_kg <= 10:
        daily = weight_kg * 100
        hourly = weight_kg * 4
    elif weight_kg <= 20:
        daily = 1000 + (weight_kg - 10) * 50
        hourly = 40 + (weight_kg - 10) * 2
    else:
        daily = 1500 + (weight_kg - 20) * 20
        hourly = 60 + (weight_kg - 20) * 1

    return {
        "value": round(daily, 6),
        "unit": "mL/day",
        "hourly_rate": round(hourly, 6),
        "hourly_unit": "mL/h",
        "formula_used": "4-2-1 rule: 100/50/20 mL/kg/day for first 10/next 10/remaining kg",
    }


@mcp.tool()
def burn_fluid_timing(
    total_24h_mL: float,
    hours_since_burn: float,
    prehospital_mL: float = 0.0,
) -> dict:
    """Purpose: Calculate burn resuscitation fluid timing targets and drip rates (first 8 h vs next 16 h allocation).
    Population: All ages (universal calculation given a total volume and hours since burn).
    Inputs:
      1. total_24h_mL (mL)
      2. hours_since_burn (hours)
      3. prehospital_mL (mL, default: 0.0)
    Outputs:
      1. first_8h_target_mL (mL)
      2. first_8h_remaining_mL (mL)
      3. first_8h_rate_mL_h (mL/h)
      4. next_16h_target_mL (mL)
      5. next_16h_rate_mL_h (mL/h)
      6. value (mL)
      7. unit (mL)
      8. formula_used (str)
    """
    first_8h_target = total_24h_mL * 0.5
    next_16h_target = total_24h_mL * 0.5

    # Subtract prehospital from first 8h allocation
    first_8h_remaining = first_8h_target - prehospital_mL

    # Calculate remaining time in first 8h period
    remaining_first8h = max(8 - hours_since_burn, 0)

    if remaining_first8h > 0:
        first8h_rate = first_8h_remaining / remaining_first8h
    else:
        first8h_rate = 0  # Past 8h window

    next16h_rate = next_16h_target / 16

    return {
        "first_8h_target_mL": round(first_8h_target, 6),
        "first_8h_remaining_mL": round(first_8h_remaining, 6),
        "first_8h_rate_mL_h": round(first8h_rate, 6),
        "next_16h_target_mL": round(next_16h_target, 6),
        "next_16h_rate_mL_h": round(next16h_rate, 6),
        "value": round(first_8h_remaining, 6),
        "unit": "mL",
        "formula_used": (
            f"First 8h: {total_24h_mL}*0.5 - {prehospital_mL} = {round(first_8h_remaining, 2)} mL "
            f"over {round(remaining_first8h, 2)}h"
        ),
    }


@mcp.tool()
def burn_rate_adjustment(
    target_vol_mL: float,
    remaining_hours: float,
    maintenance_rate_mL_h: float = 0.0,
) -> dict:
    """Purpose: Calculate adjusted IV infusion rate to deliver remaining target volume within remaining time window.
    Population: All ages (universal calculation).
    Inputs:
      1. target_vol_mL (mL)
      2. remaining_hours (hours)
      3. maintenance_rate_mL_h (mL/h, default: 0.0)
    Outputs:
      1. value (mL/h)
      2. unit (str)
      3. resuscitation_rate (mL/h, present if applicable)
      4. maintenance_rate (mL/h, present if applicable)
      5. formula_used (str)
      6. warning (str, present if applicable)
    """
    if remaining_hours <= 0:
        return {
            "value": 0,
            "unit": "mL/h",
            "warning": "No remaining time in period",
            "formula_used": "N/A - period elapsed",
        }

    resus_rate = target_vol_mL / remaining_hours
    total_rate = resus_rate + maintenance_rate_mL_h

    return {
        "value": round(total_rate, 6),
        "unit": "mL/h",
        "resuscitation_rate": round(resus_rate, 6),
        "maintenance_rate": round(maintenance_rate_mL_h, 6),
        "formula_used": f"{target_vol_mL}/{remaining_hours} + {maintenance_rate_mL_h}",
    }
