"""Nutrition tools: Harris-Benedict, TEE, protein requirements, TPN osmolarity."""

from medcal.server import mcp


@mcp.tool()
def harris_benedict(
    sex: str,
    weight_kg: float,
    height_cm: float,
    age_years: float,
) -> dict:
    """Purpose: Calculate basal energy expenditure (BEE) using Harris-Benedict equation.
    Population: Adults. Harris-Benedict validated in adults; NOT applicable to children. For pediatric energy needs use Schofield or WHO equations (not available in this tool).
    Inputs:
      1. sex ("male" / "female" / "m" / "f")
      2. weight_kg (kg)
      3. height_cm (cm)
      4. age_years (years)
    Outputs:
      1. value (kcal/day)
      2. unit (str)
      3. formula_used (str)
    """
    if sex.lower() in ("male", "m"):
        bee = 66.4730 + 13.7516 * weight_kg + 5.0033 * height_cm - 6.7550 * age_years
        formula = f"66.4730 + 13.7516*{weight_kg} + 5.0033*{height_cm} - 6.7550*{age_years}"
    else:
        bee = 655.1 + 9.563 * weight_kg + 1.850 * height_cm - 4.676 * age_years
        formula = f"655.1 + 9.563*{weight_kg} + 1.850*{height_cm} - 4.676*{age_years}"

    return {
        "value": round(bee, 6),
        "unit": "kcal/day",
        "formula_used": formula,
    }


@mcp.tool()
def tpn_target_calories(
    bee_kcal: float,
    stress_factor: float = 1.0,
    supply_fraction: float = 1.0,
) -> dict:
    """Purpose: Calculate target total energy expenditure (TEE) by applying stress and supply factors to BEE.
    Population: All ages (universal multiplier formula). Stress factor and supply fraction values differ by clinical context; adult critical care typically uses 1.2–1.5 stress factor.
    Inputs:
      1. bee_kcal (kcal/day)
      2. stress_factor (ratio, default: 1.0)
      3. supply_fraction (ratio, default: 1.0)
    Outputs:
      1. value (kcal/day)
      2. unit (str)
      3. formula_used (str)
    """
    tee = bee_kcal * stress_factor * supply_fraction
    return {
        "value": round(tee, 6),
        "unit": "kcal/day",
        "formula_used": f"{bee_kcal} * {stress_factor} * {supply_fraction}",
    }


@mcp.tool()
def tpn_protein(
    weight_kg: float,
    protein_g_per_kg: float = 1.5,
) -> dict:
    """Purpose: Calculate daily protein requirement for TPN/enteral nutrition.
    Population: All ages. Default 1.5 g/kg/day is a common adult critical care target; adjust protein_g_per_kg per protocol (pediatric neonates may need 3–4 g/kg/day; children 1.5–3 g/kg/day).
    Inputs:
      1. weight_kg (kg)
      2. protein_g_per_kg (g/kg/day, default: 1.5)
    Outputs:
      1. value (g/day)
      2. unit (str)
      3. protein_kcal (kcal/day)
      4. formula_used (str)
    """
    protein = weight_kg * protein_g_per_kg
    protein_kcal = protein * 4  # 4 kcal/g from amino acids

    return {
        "value": round(protein, 6),
        "unit": "g/day",
        "protein_kcal": round(protein_kcal, 6),
        "formula_used": f"{weight_kg} * {protein_g_per_kg}",
    }


@mcp.tool()
def tpn_osmolarity(
    glucose_g: float,
    amino_acid_g: float,
    lipid_g: float = 0.0,
) -> dict:
    """Purpose: Calculate TPN osmolarity to determine safe administration route.
    Population: All ages. Osmolarity >900 mOsm/L requires central venous access in both adults and children; peripheral TPN limit is lower for neonates (~800 mOsm/L).
    Inputs:
      1. glucose_g (g/L)
      2. amino_acid_g (g/L)
      3. lipid_g (g/L, default: 0.0)
    Outputs:
      1. value (mOsm/L)
      2. unit (str)
      3. formula_used (str)
      4. route_recommendation (str)
    """
    osm = glucose_g * 5 + amino_acid_g * 8 + lipid_g * 1.5
    route = "Central venous access required" if osm > 900 else "Peripheral access may be acceptable"

    return {
        "value": round(osm, 6),
        "unit": "mOsm/L",
        "formula_used": f"{glucose_g}*5 + {amino_acid_g}*8 + {lipid_g}*1.5",
        "route_recommendation": route,
    }
