"""Echocardiography tools: Devereux LV mass, LVMI."""

from medcal.server import mcp


@mcp.tool()
def devereux_lv_mass(
    lvedd_cm: float,
    ivsd_cm: float,
    pwd_cm: float,
) -> dict:
    """Purpose: Calculate left ventricular mass (Devereux formula) from M-mode echo measurements.
    Population: Adults. Devereux formula validated in adults; LVH thresholds and z-score norms for children require age- and sex-specific pediatric reference tables.
    Inputs:
      1. lvedd_cm (cm)
      2. ivsd_cm (cm)
      3. pwd_cm (cm)
    Outputs:
      1. value (g)
      2. unit (str)
      3. formula_used (str)
    """
    total = lvedd_cm + ivsd_cm + pwd_cm
    lvm = 0.8 * (1.04 * (total ** 3 - lvedd_cm ** 3)) + 0.6
    return {
        "value": round(lvm, 6),
        "unit": "g",
        "formula_used": f"0.8 * (1.04 * (({lvedd_cm}+{ivsd_cm}+{pwd_cm})^3 - {lvedd_cm}^3)) + 0.6",
    }


@mcp.tool()
def lv_mass_index(
    lvm_g: float,
    bsa_m2: float,
) -> dict:
    """Purpose: Calculate left ventricular mass index (LVMI = LVM / BSA).
    Population: Adults. LVH thresholds (>115 g/m² male, >95 g/m² female) are adult criteria (ASE guidelines). For children, BSA-indexed norms differ by age and sex; use pediatric z-score tables.
    Inputs:
      1. lvm_g (g)
      2. bsa_m2 (m^2)
    Outputs:
      1. value (g/m^2)
      2. unit (str)
      3. formula_used (str)
      4. interpretation (str)
    """
    lvmi = lvm_g / bsa_m2
    return {
        "value": round(lvmi, 6),
        "unit": "g/m^2",
        "formula_used": f"{lvm_g} / {bsa_m2}",
        "interpretation": "LVH threshold: >115 g/m^2 (male), >95 g/m^2 (female)",
    }
