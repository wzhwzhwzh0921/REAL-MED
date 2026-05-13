"""Dialysis tools: Daugirdas Kt/V, residual clearance, renal Kt/V, weekly total Kt/V."""

import math

from medcal.server import mcp


@mcp.tool()
def daugirdas_ktv(
    bun_pre_mg_dL: float,
    bun_post_mg_dL: float,
    t_hours: float,
    uf_L: float,
    v_L: float,
) -> dict:
    """Purpose: Calculate single-pool Kt/V for hemodialysis adequacy (Daugirdas II formula).
    Population: Adults. Daugirdas II equation validated in adult HD patients. Target spKt/V ≥1.2 per adult KDOQI guidelines. Pediatric HD adequacy uses the same target but V is estimated by pediatric-specific methods.
    Inputs:
      1. bun_pre_mg_dL (mg/dL)
      2. bun_post_mg_dL (mg/dL)
      3. t_hours (hours)
      4. uf_L (L)
      5. v_L (L)
    Outputs:
      1. value (dimensionless)
      2. unit (str)
      3. r_ratio (ratio)
      4. formula_used (str)
      5. interpretation (str)
    """
    r = bun_post_mg_dL / bun_pre_mg_dL
    ktv = -math.log(r - 0.008 * t_hours) + (4 - 3.5 * r) * (uf_L / v_L)

    interp = "Adequate (>=1.2)" if ktv >= 1.2 else "Inadequate (<1.2)"

    return {
        "value": round(ktv, 6),
        "unit": "dimensionless",
        "r_ratio": round(r, 6),
        "formula_used": f"-ln({round(r, 4)} - 0.008*{t_hours}) + (4 - 3.5*{round(r, 4)})*({uf_L}/{v_L})",
        "interpretation": interp,
    }


@mcp.tool()
def residual_renal_clearance(
    u_urea_mg_dL: float,
    urine_vol_mL: float,
    collection_time_min: float,
    p_urea_mg_dL: float,
    plasma_correction_factor: float = 0.9,
) -> dict:
    """Purpose: Calculate residual renal urea clearance (KRU) from timed urine collection.
    Population: All ages (universal clearance calculation). Used in both adult and pediatric peritoneal dialysis adequacy assessment.
    Inputs:
      1. u_urea_mg_dL (mg/dL)
      2. urine_vol_mL (mL)
      3. collection_time_min (min)
      4. p_urea_mg_dL (mg/dL)
      5. plasma_correction_factor (ratio, default: 0.9)
    Outputs:
      1. value (mL/min)
      2. unit (str)
      3. formula_used (str)
    """
    denom = collection_time_min * (plasma_correction_factor * p_urea_mg_dL)
    kru = (u_urea_mg_dL * urine_vol_mL) / denom
    return {
        "value": round(kru, 6),
        "unit": "mL/min",
        "formula_used": (
            f"({u_urea_mg_dL} * {urine_vol_mL}) / "
            f"({collection_time_min} * ({plasma_correction_factor} * {p_urea_mg_dL}))"
        ),
    }


@mcp.tool()
def renal_ktv(
    kru_mL_min: float,
    watson_v_L: float,
) -> dict:
    """Purpose: Calculate daily and weekly renal Kt/V from residual renal clearance.
    Population: Adults. Supply Watson TBW (from watson_tbw) as the V denominator; pediatric V should use age-appropriate TBW estimates.
    Inputs:
      1. kru_mL_min (mL/min)
      2. watson_v_L (L)
    Outputs:
      1. value (per week)
      2. unit (str)
      3. daily_ktv (per day)
      4. weekly_ktv (per week)
      5. formula_used (str)
    """
    v_mL = watson_v_L * 1000
    daily = (kru_mL_min * 1440) / v_mL
    weekly = daily * 7

    return {
        "value": round(weekly, 6),
        "unit": "per week",
        "daily_ktv": round(daily, 6),
        "weekly_ktv": round(weekly, 6),
        "formula_used": f"({kru_mL_min} * 1440) / ({watson_v_L} * 1000) * 7",
    }


@mcp.tool()
def weekly_total_ktv(
    peritoneal_ktv_weekly: float,
    renal_ktv_weekly: float,
) -> dict:
    """Purpose: Calculate total weekly Kt/V for peritoneal dialysis adequacy (peritoneal + residual renal contributions).
    Population: Adults. Target total weekly Kt/V ≥1.7 per adult KDOQI PD guidelines (2006). Pediatric PD targets may differ by age and modality.
    Inputs:
      1. peritoneal_ktv_weekly (per week)
      2. renal_ktv_weekly (per week)
    Outputs:
      1. value (per week)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    total = peritoneal_ktv_weekly + renal_ktv_weekly
    interp = "Adequate (>=1.7)" if total >= 1.7 else "Inadequate (<1.7)"

    return {
        "value": round(total, 6),
        "unit": "per week",
        "formula_used": f"{peritoneal_ktv_weekly} + {renal_ktv_weekly}",
        "interpretation": interp,
    }
