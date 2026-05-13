"""Oncology tools: Calvert carboplatin, paclitaxel dosing."""

from medcal.server import mcp


@mcp.tool()
def calvert_carboplatin(
    target_auc: float,
    crcl_mL_min: float,
) -> dict:
    """Purpose: Calculate carboplatin dose using the Calvert formula (dose = AUC × [GFR + 25]).
    Population: Adults. Calvert formula uses adult-derived GFR estimates. For children, carboplatin dosing is commonly BSA-based (mg/m²) rather than AUC-based; confirm with oncology protocol.
    Notes: Use CrCl from Cockcroft-Gault as GFR estimate; FDA recommends capping CrCl at 125 mL/min for female patients in this formula.
    Inputs:
      1. target_auc (mg*h/mL)
      2. crcl_mL_min (mL/min)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. formula_used (str)
    """
    dose = target_auc * (crcl_mL_min + 25)
    return {
        "value": round(dose, 6),
        "unit": "mg",
        "formula_used": f"{target_auc} * ({crcl_mL_min} + 25)",
    }


@mcp.tool()
def paclitaxel_dose(
    bsa_m2: float,
    dose_mg_per_m2: float = 175.0,
) -> dict:
    """Purpose: Calculate paclitaxel dose from body surface area (BSA-based chemotherapy dosing).
    Population: All ages. BSA-based dosing is used for both adults and children; supply the appropriate dose_mg_per_m2 per protocol (default 175 mg/m² is a common adult regimen).
    Inputs:
      1. bsa_m2 (m^2)
      2. dose_mg_per_m2 (mg/m^2, default: 175.0)
    Outputs:
      1. value (mg)
      2. unit (str)
      3. formula_used (str)
    """
    dose = bsa_m2 * dose_mg_per_m2
    return {
        "value": round(dose, 6),
        "unit": "mg",
        "formula_used": f"{bsa_m2} * {dose_mg_per_m2}",
    }
