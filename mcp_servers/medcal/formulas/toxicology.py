"""Toxicology tools: NAC 3-bag and 2-bag protocols for acetaminophen overdose."""

from medcal.server import mcp


@mcp.tool()
def nac_three_bag(
    weight_kg: float,
    concentration_mg_mL: float = 200.0,
) -> dict:
    """Purpose: Calculate N-acetylcysteine (NAC) doses for the standard three-bag IV protocol in acetaminophen overdose (150 + 50 + 100 mg/kg).
    Population: Adults and adolescents. Weight is capped at 100 kg (standard protocol cap). For infants and young children, confirm protocol compatibility with institutional guidelines; same mg/kg doses apply but fluid volumes must be adjusted to avoid fluid overload.
    Inputs:
      1. weight_kg (kg)
      2. concentration_mg_mL (mg/mL, default: 200.0)
    Outputs:
      1. value (mg)
      2. unit (mg)
      3. bag1_dose_mg (mg)
      4. bag1_nac_volume_mL (mL)
      5. bag1_diluent (str)
      6. bag1_duration (str)
      7. bag2_dose_mg (mg)
      8. bag2_nac_volume_mL (mL)
      9. bag2_diluent (str)
      10. bag2_duration (str)
      11. bag3_dose_mg (mg)
      12. bag3_nac_volume_mL (mL)
      13. bag3_diluent (str)
      14. bag3_duration (str)
      15. weight_used_kg (kg)
      16. formula_used (str)
    """
    w = min(weight_kg, 100)

    bag1_dose = w * 150
    bag1_vol = bag1_dose / concentration_mg_mL

    bag2_dose = w * 50
    bag2_vol = bag2_dose / concentration_mg_mL

    bag3_dose = w * 100
    bag3_vol = bag3_dose / concentration_mg_mL

    return {
        "value": round(bag1_dose + bag2_dose + bag3_dose, 2),
        "unit": "mg (total NAC)",
        "bag1_dose_mg": round(bag1_dose, 2),
        "bag1_nac_volume_mL": round(bag1_vol, 2),
        "bag1_diluent": "200 mL D5W",
        "bag1_duration": "15-60 min",
        "bag2_dose_mg": round(bag2_dose, 2),
        "bag2_nac_volume_mL": round(bag2_vol, 2),
        "bag2_diluent": "500 mL D5W",
        "bag2_duration": "4 hours",
        "bag3_dose_mg": round(bag3_dose, 2),
        "bag3_nac_volume_mL": round(bag3_vol, 2),
        "bag3_diluent": "1000 mL D5W",
        "bag3_duration": "16 hours",
        "weight_used_kg": w,
        "formula_used": f"150+50+100 mg/kg protocol",
    }


@mcp.tool()
def nac_two_bag(
    weight_kg: float,
    concentration_mg_mL: float = 200.0,
) -> dict:
    """Purpose: Calculate N-acetylcysteine (NAC) doses for the two-bag IV protocol in acetaminophen overdose (200 + 100 mg/kg).
    Population: Adults and adolescents. Weight is capped at 100 kg. For small children, confirm fluid volumes with institutional protocols to avoid overload.
    Inputs:
      1. weight_kg (kg)
      2. concentration_mg_mL (mg/mL, default: 200.0)
    Outputs:
      1. value (mg)
      2. unit (mg)
      3. bag1_dose_mg (mg)
      4. bag1_nac_volume_mL (mL)
      5. bag1_diluent (str)
      6. bag1_duration (str)
      7. bag2_dose_mg (mg)
      8. bag2_nac_volume_mL (mL)
      9. bag2_diluent (str)
      10. bag2_duration (str)
      11. weight_used_kg (kg)
      12. formula_used (str)
    """
    w = min(weight_kg, 100)

    bag1_dose = w * 200
    bag1_vol = bag1_dose / concentration_mg_mL

    bag2_dose = w * 100
    bag2_vol = bag2_dose / concentration_mg_mL

    return {
        "value": round(bag1_dose + bag2_dose, 2),
        "unit": "mg (total NAC)",
        "bag1_dose_mg": round(bag1_dose, 2),
        "bag1_nac_volume_mL": round(bag1_vol, 2),
        "bag1_diluent": "500 mL D5W",
        "bag1_duration": "4 hours",
        "bag2_dose_mg": round(bag2_dose, 2),
        "bag2_nac_volume_mL": round(bag2_vol, 2),
        "bag2_diluent": "1000 mL D5W",
        "bag2_duration": "16 hours",
        "weight_used_kg": w,
        "formula_used": f"200+100 mg/kg protocol",
    }
