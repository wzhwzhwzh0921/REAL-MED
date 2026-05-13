"""Acid-base tools: anion gap, corrected AG, delta-delta, Winters formula."""

from medcal.server import mcp


@mcp.tool()
def anion_gap(
    na_mEq_L: float,
    cl_mEq_L: float,
    hco3_mEq_L: float,
) -> dict:
    """Purpose: Calculate serum anion gap (Na − Cl − HCO3).
    Population: All ages. Normal AG cutoff of 12 mEq/L is adult reference range; the same cutoff is generally applied to children. Always correct for albumin with anion_gap_albumin_corrected in hypoalbuminaemia.
    Inputs:
      1. na_mEq_L (mEq/L)
      2. cl_mEq_L (mEq/L)
      3. hco3_mEq_L (mEq/L)
    Outputs:
      1. value (mEq/L)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    ag = na_mEq_L - (cl_mEq_L + hco3_mEq_L)
    interp = "Normal" if ag <= 12 else "Elevated (anion gap metabolic acidosis)"
    return {
        "value": round(ag, 6),
        "unit": "mEq/L",
        "formula_used": f"{na_mEq_L} - ({cl_mEq_L} + {hco3_mEq_L})",
        "interpretation": interp,
    }


@mcp.tool()
def anion_gap_albumin_corrected(
    ag_mEq_L: float,
    albumin_g_dL: float,
) -> dict:
    """Purpose: Calculate albumin-corrected anion gap to unmask HAGMA in hypoalbuminaemia.
    Population: All ages (universal correction formula).
    Inputs:
      1. ag_mEq_L (mEq/L)
      2. albumin_g_dL (g/dL)
    Outputs:
      1. value (mEq/L)
      2. unit (str)
      3. formula_used (str)
    """
    ag_corr = ag_mEq_L + 2.5 * (4.0 - albumin_g_dL)
    return {
        "value": round(ag_corr, 6),
        "unit": "mEq/L",
        "formula_used": f"{ag_mEq_L} + 2.5 * (4.0 - {albumin_g_dL})",
    }


@mcp.tool()
def delta_delta_ratio(
    ag_corrected_mEq_L: float,
    hco3_mEq_L: float,
    normal_ag: float = 12.0,
    normal_hco3: float = 24.0,
) -> dict:
    """Purpose: Calculate delta-delta ratio to identify mixed acid-base disorders in HAGMA.
    Population: All ages (universal formula). Normal AG reference of 12 and HCO3 reference of 24 are adult values; adjust if patient-specific normals differ.
    Inputs:
      1. ag_corrected_mEq_L (mEq/L)
      2. hco3_mEq_L (mEq/L)
      3. normal_ag (mEq/L, default: 12.0)
      4. normal_hco3 (mEq/L, default: 24.0)
    Outputs:
      1. value (ratio or "inf")
      2. unit (str)
      3. delta_ag (mEq/L)
      4. delta_hco3 (mEq/L)
      5. formula_used (str)
      6. interpretation (str)
    """
    delta_ag = ag_corrected_mEq_L - normal_ag
    delta_hco3 = normal_hco3 - hco3_mEq_L

    if delta_hco3 == 0:
        ratio = float("inf")
        interp = "No HCO3 change; possible metabolic alkalosis if AG elevated"
    else:
        ratio = delta_ag / delta_hco3
        if ratio < 1:
            interp = "Combined HAGMA + non-anion gap metabolic acidosis (NAGMA)"
        elif ratio <= 2:
            interp = "Pure high anion gap metabolic acidosis (HAGMA)"
        else:
            interp = "HAGMA + concurrent metabolic alkalosis"

    return {
        "value": round(ratio, 6) if ratio != float("inf") else "inf",
        "unit": "ratio",
        "delta_ag": round(delta_ag, 6),
        "delta_hco3": round(delta_hco3, 6),
        "formula_used": f"({ag_corrected_mEq_L} - {normal_ag}) / ({normal_hco3} - {hco3_mEq_L})",
        "interpretation": interp,
    }


@mcp.tool()
def winters_formula(
    hco3_mEq_L: float,
) -> dict:
    """Purpose: Calculate expected respiratory compensation (PaCO2) for metabolic acidosis using Winters formula.
    Population: Adults. Winters formula (1.5 × HCO3 + 8 ± 2) validated in adults. For children, expected PaCO2 = 1.5 × HCO3 + 6 (slightly different — do not use this tool for pediatric respiratory compensation).
    Inputs:
      1. hco3_mEq_L (mEq/L)
    Outputs:
      1. value (mmHg)
      2. unit (str)
      3. range_low (mmHg)
      4. range_high (mmHg)
      5. formula_used (str)
    """
    expected = 1.5 * hco3_mEq_L + 8
    return {
        "value": round(expected, 6),
        "unit": "mmHg",
        "range_low": round(expected - 2, 6),
        "range_high": round(expected + 2, 6),
        "formula_used": f"1.5 * {hco3_mEq_L} + 8 (+/- 2)",
    }
