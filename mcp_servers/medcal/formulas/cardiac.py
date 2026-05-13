"""Cardiac electrophysiology tools: QTc, dofetilide dosing, monitoring."""

import math

from medcal.server import mcp


@mcp.tool()
def bazett_qtc(
    qt_ms: float,
    rr_s: float,
) -> dict:
    """Purpose: Calculate corrected QT interval (Bazett formula).
    Population: All ages. Normal QTc threshold used here is <440 ms (adult general cutoff); note that QTc upper limits differ by sex (male <450 ms, female <460 ms) and may differ for children.
    Inputs:
      1. qt_ms (ms)
      2. rr_s (s)
    Outputs:
      1. value (ms)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    qtc = qt_ms / math.sqrt(rr_s)
    interp = "Normal" if qtc < 440 else ("Borderline" if qtc < 500 else "Prolonged")
    return {
        "value": round(qtc, 6),
        "unit": "ms",
        "formula_used": f"{qt_ms} / sqrt({rr_s})",
        "interpretation": interp,
    }


@mcp.tool()
def qtc_change_percent(
    baseline_qtc_ms: float,
    post_qtc_ms: float,
) -> dict:
    """Purpose: Calculate QTc percent change from baseline (drug-induced QT monitoring).
    Population: All ages (universal calculation).
    Inputs:
      1. baseline_qtc_ms (ms)
      2. post_qtc_ms (ms)
    Outputs:
      1. value (%)
      2. unit (str)
      3. formula_used (str)
      4. warning (str, present if applicable)
    """
    change = ((post_qtc_ms - baseline_qtc_ms) / baseline_qtc_ms) * 100
    warning = None
    if change > 15:
        warning = "QTc increased >15% from baseline; dose reduction may be needed"
    if post_qtc_ms > 500:
        warning = "Absolute QTc >500 ms; consider drug discontinuation"

    result = {
        "value": round(change, 6),
        "unit": "%",
        "formula_used": f"(({post_qtc_ms} - {baseline_qtc_ms}) / {baseline_qtc_ms}) * 100",
    }
    if warning:
        result["warning"] = warning
    return result


@mcp.tool()
def dofetilide_dose_by_crcl(
    crcl_mL_min: float,
) -> dict:
    """Purpose: Calculate dofetilide (Tikosyn) dose based on creatinine clearance.
    Population: Adults only. Dofetilide is contraindicated in CrCl <20 mL/min. Not used in pediatrics.
    Inputs:
      1. crcl_mL_min (mL/min)
    Outputs:
      1. value (mcg)
      2. unit (str)
      3. frequency (str)
      4. formula_used (str)
      5. interpretation (str)
    """
    if crcl_mL_min > 60:
        dose = 500
        freq = "BID"
        interp = "Standard dose"
    elif crcl_mL_min >= 40:
        dose = 250
        freq = "BID"
        interp = "Reduced dose for moderate renal impairment"
    elif crcl_mL_min >= 20:
        dose = 125
        freq = "BID"
        interp = "Reduced dose for severe renal impairment"
    else:
        dose = 0
        freq = "N/A"
        interp = "Contraindicated: CrCl < 20 mL/min"

    return {
        "value": dose,
        "unit": "mcg",
        "frequency": freq,
        "formula_used": f"CrCl-based stratification: CrCl = {round(crcl_mL_min, 2)} mL/min",
        "interpretation": interp,
    }


@mcp.tool()
def monitoring_window(
    hours_after_dose: float,
    window_start_h: float = 2.0,
    window_end_h: float = 3.0,
) -> dict:
    """Purpose: Determine whether a given time falls within a monitoring window (e.g., QTc check 2–3 h post-dose).
    Population: All ages (universal time-window check).
    Inputs:
      1. hours_after_dose (hours)
      2. window_start_h (hours, default: 2.0)
      3. window_end_h (hours, default: 3.0)
    Outputs:
      1. value (0 or 1)
      2. unit (str)
      3. in_window (True/False)
      4. formula_used (str)
    """
    in_window = window_start_h <= hours_after_dose <= window_end_h
    return {
        "value": 1 if in_window else 0,
        "unit": "bool",
        "in_window": in_window,
        "formula_used": f"{window_start_h} <= {hours_after_dose} <= {window_end_h}",
    }


@mcp.tool()
def aminophylline_conversion(
    aminophylline_dose_mg: float,
) -> dict:
    """Purpose: Convert aminophylline dose to theophylline-equivalent dose (aminophylline is 80% theophylline by weight).
    Population: All ages (universal conversion factor).
    Inputs:
      1. aminophylline_dose_mg (mg)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. formula_used (str)
    """
    theo = aminophylline_dose_mg * 0.8
    return {
        "value": round(theo, 6),
        "unit": "mg",
        "formula_used": f"{aminophylline_dose_mg} * 0.8",
    }
