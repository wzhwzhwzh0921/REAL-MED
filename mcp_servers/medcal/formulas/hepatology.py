"""Hepatology tools: MELD, MELD-Na."""

import math

from medcal.server import mcp


@mcp.tool()
def meld_score(
    creatinine_mg_dL: float,
    bilirubin_mg_dL: float,
    inr: float,
    on_dialysis: bool = False,
) -> dict:
    """Purpose: Calculate the MELD (Model for End-Stage Liver Disease) score for liver transplant prioritization.
    Population: Adults (≥18 years). For children <12 years, use the PELD (Pediatric End-Stage Liver Disease) score instead. Creatinine is capped at 4.0 mg/dL; dialysis sets creatinine to 4.0 automatically.
    Inputs:
      1. creatinine_mg_dL (mg/dL)
      2. bilirubin_mg_dL (mg/dL)
      3. inr (ratio)
      4. on_dialysis (True/False, default: False)
    Outputs:
      1. value (score)
      2. unit (str)
      3. formula_used (str)
    """
    cr = 4.0 if on_dialysis else max(creatinine_mg_dL, 1.0)
    bili = max(bilirubin_mg_dL, 1.0)
    inr_val = max(inr, 1.0)

    meld = 10 * (0.957 * math.log(cr) + 0.378 * math.log(bili) + 1.120 * math.log(inr_val) + 0.643)
    meld = min(meld, 40)

    return {
        "value": round(meld, 6),
        "unit": "score",
        "formula_used": f"10 * (0.957*ln({cr}) + 0.378*ln({bili}) + 1.120*ln({inr_val}) + 0.643)",
    }


@mcp.tool()
def meld_na_score(
    meld_raw: float,
    na_mEq_L: float,
) -> dict:
    """Purpose: Calculate the MELD-Na score (UNOS MELD incorporating sodium for transplant listing).
    Population: Adults. Na is capped between 120–135 mEq/L per UNOS guidelines. Not used in pediatric liver allocation.
    Inputs:
      1. meld_raw (score)
      2. na_mEq_L (mEq/L)
    Outputs:
      1. value (score)
      2. unit (str)
      3. na_capped (mEq/L)
      4. formula_used (str)
    """
    na_capped = max(120, min(na_mEq_L, 135))
    meld_na = meld_raw + 1.59 * (135 - na_capped)

    return {
        "value": round(meld_na, 6),
        "unit": "score",
        "na_capped": na_capped,
        "formula_used": f"{meld_raw} + 1.59 * (135 - {na_capped})",
    }
