"""Formula metadata registry — maps canonical tool IDs to metadata."""

FORMULA_REGISTRY = {
    # === Renal (3) ===
    "cockcroft_gault_crcl": {
        "domain": "renal",
        "aliases": ["CrCl", "CG", "Cockcroft-Gault"],
        "inputs": ["age_years", "weight_kg", "sex", "scr_mg_dL"],
        "outputs": ["crcl_mL_min"],
        "references": ["Cockcroft DW, Gault MH. Nephron 1976;16:31-41"],
    },
    "crcl_stratum": {
        "domain": "renal",
        "aliases": ["CrCl stratum", "renal dose tier"],
        "inputs": ["crcl_mL_min"],
        "outputs": ["stratum", "dose_factor"],
        "references": [],
    },
    "dose_adjustment_assessment": {
        "domain": "renal",
        "aliases": ["renal dose adjustment"],
        "inputs": ["crcl_mL_min", "threshold"],
        "outputs": ["needs_adjustment"],
        "references": [],
    },
    # === Body Metrics (6) ===
    "ideal_body_weight": {
        "domain": "body_metrics",
        "aliases": ["IBW", "Devine IBW"],
        "inputs": ["sex", "height_cm"],
        "outputs": ["ibw_kg"],
        "references": ["Devine BJ. Drug Intell Clin Pharm 1974;8:650-5"],
    },
    "adjusted_body_weight": {
        "domain": "body_metrics",
        "aliases": ["AdjBW"],
        "inputs": ["ibw_kg", "tbw_kg", "factor"],
        "outputs": ["adjbw_kg"],
        "references": [],
    },
    "predicted_body_weight": {
        "domain": "body_metrics",
        "aliases": ["PBW", "ARDSNet PBW"],
        "inputs": ["sex", "height_cm"],
        "outputs": ["pbw_kg"],
        "references": ["ARDSNet NEJM 2000;342:1301-8"],
    },
    "bsa_dubois": {
        "domain": "body_metrics",
        "aliases": ["BSA DuBois"],
        "inputs": ["height_cm", "weight_kg"],
        "outputs": ["bsa_m2"],
        "references": ["DuBois D, DuBois EF. Arch Intern Med 1916;17:863-71"],
    },
    "bsa_mosteller": {
        "domain": "body_metrics",
        "aliases": ["BSA Mosteller"],
        "inputs": ["height_cm", "weight_kg"],
        "outputs": ["bsa_m2"],
        "references": ["Mosteller RD. NEJM 1987;317:1098"],
    },
    "watson_tbw": {
        "domain": "body_metrics",
        "aliases": ["TBW", "Watson TBW"],
        "inputs": ["sex", "age_years", "height_cm", "weight_kg"],
        "outputs": ["tbw_L"],
        "references": ["Watson PE et al. Am J Clin Nutr 1980;33:27-39"],
    },
    # === Pharmacokinetics (7) ===
    "elimination_rate_constant": {
        "domain": "pharmacokinetics",
        "aliases": ["ke"],
        "inputs": ["half_life_h"],
        "outputs": ["ke_per_h"],
        "references": [],
    },
    "elimination_half_life": {
        "domain": "pharmacokinetics",
        "aliases": ["t½"],
        "inputs": ["ke_per_h"],
        "outputs": ["half_life_h"],
        "references": [],
    },
    "volume_of_distribution": {
        "domain": "pharmacokinetics",
        "aliases": ["Vd"],
        "inputs": ["vd_L_per_kg", "weight_kg"],
        "outputs": ["vd_L"],
        "references": [],
    },
    "steady_state_cmax": {
        "domain": "pharmacokinetics",
        "aliases": ["Cmax"],
        "inputs": ["dose_mg", "t_inf_h", "vd_L", "ke_per_h", "tau_h"],
        "outputs": ["cmax_mg_L"],
        "references": [],
    },
    "steady_state_cmin": {
        "domain": "pharmacokinetics",
        "aliases": ["Cmin"],
        "inputs": ["cmax_mg_L", "ke_per_h", "tau_h", "t_inf_h"],
        "outputs": ["cmin_mg_L"],
        "references": [],
    },
    "percent_time_above_mic": {
        "domain": "pharmacokinetics",
        "aliases": ["%T>MIC", "PK/PD target"],
        "inputs": ["cmax_mg_L", "cmin_mg_L", "ke_per_h", "t_inf_h", "tau_h", "mic_mg_L"],
        "outputs": ["pct_t_above_mic"],
        "references": [],
    },
    "sotalol_renal_dosing": {
        "domain": "pharmacokinetics",
        "aliases": ["Scr unit conversion"],
        "inputs": ["scr_value", "scr_unit"],
        "outputs": ["scr_mg_dL"],
        "references": [],
    },
    # === Vancomycin (4) ===
    "vancomycin_clearance": {
        "domain": "vancomycin",
        "aliases": ["Vanco Ke", "Matzke Ke"],
        "inputs": ["crcl_mL_min"],
        "outputs": ["ke_per_h"],
        "references": ["Matzke GR et al. Clin Pharmacol Ther 1984;36:803-10"],
    },
    "vancomycin_auc": {
        "domain": "vancomycin",
        "aliases": ["Vanco AUC", "AUC24"],
        "inputs": ["dose_mg", "interval_h", "clearance_L_h"],
        "outputs": ["auc24"],
        "references": ["Rybak MJ et al. Am J Health Syst Pharm 2020;77:835-64"],
    },
    "vancomycin_dosing": {
        "domain": "vancomycin",
        "aliases": ["Vanco maintenance dose"],
        "inputs": ["target_auc", "clearance_L_h", "interval_h"],
        "outputs": ["dose_mg"],
        "references": [],
    },
    "vancomycin_loading": {
        "domain": "vancomycin",
        "aliases": ["Vanco loading"],
        "inputs": ["weight_kg", "target_mg_per_kg"],
        "outputs": ["loading_dose_mg"],
        "references": [],
    },
    # === Cardiac Electrophysiology (5) ===
    "bazett_qtc": {
        "domain": "cardiac",
        "aliases": ["QTc", "Bazett QTc"],
        "inputs": ["qt_ms", "rr_s"],
        "outputs": ["qtc_ms"],
        "references": ["Bazett HC. Heart 1920;7:353-70"],
    },
    "qtc_change_percent": {
        "domain": "cardiac",
        "aliases": ["QTc change"],
        "inputs": ["baseline_qtc_ms", "post_qtc_ms"],
        "outputs": ["change_pct"],
        "references": [],
    },
    "dofetilide_dose_by_crcl": {
        "domain": "cardiac",
        "aliases": ["Tikosyn dosing", "dofetilide dose"],
        "inputs": ["crcl_mL_min"],
        "outputs": ["dose_mcg", "frequency"],
        "references": ["Tikosyn (dofetilide) prescribing information"],
    },
    "monitoring_window": {
        "domain": "cardiac",
        "aliases": ["QTc monitoring window"],
        "inputs": ["hours_after_dose", "window_start_h", "window_end_h"],
        "outputs": ["in_window"],
        "references": [],
    },
    "aminophylline_conversion": {
        "domain": "cardiac",
        "aliases": ["aminophylline to theophylline"],
        "inputs": ["aminophylline_dose_mg"],
        "outputs": ["theophylline_dose_mg"],
        "references": [],
    },
    # === Hemodynamics (6) ===
    "arterial_oxygen_content": {
        "domain": "hemodynamics",
        "aliases": ["CaO2"],
        "inputs": ["hb_g_dL", "sao2_fraction", "pao2_mmHg"],
        "outputs": ["cao2_mL_dL"],
        "references": [],
    },
    "venous_oxygen_content": {
        "domain": "hemodynamics",
        "aliases": ["CvO2"],
        "inputs": ["hb_g_dL", "svo2_fraction", "pvo2_mmHg"],
        "outputs": ["cvo2_mL_dL"],
        "references": [],
    },
    "avdo2": {
        "domain": "hemodynamics",
        "aliases": ["a-vDO2"],
        "inputs": ["cao2_mL_dL", "cvo2_mL_dL"],
        "outputs": ["avdo2_mL_dL"],
        "references": [],
    },
    "fick_cardiac_output": {
        "domain": "hemodynamics",
        "aliases": ["Fick CO"],
        "inputs": ["vo2_mL_min", "cao2_mL_dL", "cvo2_mL_dL"],
        "outputs": ["co_L_min"],
        "references": [],
    },
    "svr_calculation": {
        "domain": "hemodynamics",
        "aliases": ["SVR"],
        "inputs": ["map_mmHg", "cvp_mmHg", "co_L_min", "unit"],
        "outputs": ["svr"],
        "references": [],
    },
    "oxygen_delivery": {
        "domain": "hemodynamics",
        "aliases": ["DO2", "DO2I"],
        "inputs": ["co_L_min", "cao2_mL_dL", "bsa_m2"],
        "outputs": ["do2", "do2i"],
        "references": [],
    },
    # === Respiratory (4) ===
    "alveolar_gas_equation": {
        "domain": "respiratory",
        "aliases": ["PAO2"],
        "inputs": ["fio2", "paco2_mmHg", "patm_mmHg", "rq"],
        "outputs": ["pao2_mmHg"],
        "references": [],
    },
    "aa_gradient": {
        "domain": "respiratory",
        "aliases": ["A-a gradient"],
        "inputs": ["pao2_calculated_mmHg", "pao2_measured_mmHg"],
        "outputs": ["aa_gradient_mmHg"],
        "references": [],
    },
    "aa_gradient_normal": {
        "domain": "respiratory",
        "aliases": ["expected A-a gradient"],
        "inputs": ["age_years"],
        "outputs": ["normal_aa_mmHg"],
        "references": [],
    },
    "protective_tidal_volume": {
        "domain": "respiratory",
        "aliases": ["Vt", "ARDSNet tidal volume"],
        "inputs": ["pbw_kg", "ml_per_kg"],
        "outputs": ["vt_mL"],
        "references": ["ARDSNet NEJM 2000;342:1301-8"],
    },
    # === Acid-Base (4) ===
    "anion_gap": {
        "domain": "acid_base",
        "aliases": ["AG"],
        "inputs": ["na_mEq_L", "cl_mEq_L", "hco3_mEq_L"],
        "outputs": ["ag_mEq_L"],
        "references": [],
    },
    "anion_gap_albumin_corrected": {
        "domain": "acid_base",
        "aliases": ["corrected AG"],
        "inputs": ["ag_mEq_L", "albumin_g_dL"],
        "outputs": ["ag_corrected_mEq_L"],
        "references": [],
    },
    "delta_delta_ratio": {
        "domain": "acid_base",
        "aliases": ["delta-delta", "Delta ratio"],
        "inputs": ["ag_corrected_mEq_L", "hco3_mEq_L"],
        "outputs": ["ratio", "interpretation"],
        "references": [],
    },
    "winters_formula": {
        "domain": "acid_base",
        "aliases": ["Winters", "expected PaCO2"],
        "inputs": ["hco3_mEq_L"],
        "outputs": ["expected_paco2_mmHg"],
        "references": ["Winters RW. J Pediatr 1967;70:244-7"],
    },
    # === Osmolality (5) ===
    "serum_osmolality": {
        "domain": "osmolality",
        "aliases": ["calculated osm"],
        "inputs": ["na_mEq_L", "glucose_mg_dL", "bun_mg_dL", "ethanol_mg_dL"],
        "outputs": ["osm_mOsm_kg"],
        "references": [],
    },
    "osmolal_gap": {
        "domain": "osmolality",
        "aliases": ["osm gap"],
        "inputs": ["measured_osm_mOsm_kg", "calculated_osm_mOsm_kg"],
        "outputs": ["gap_mOsm_kg"],
        "references": [],
    },
    "toxic_alcohol_estimation": {
        "domain": "osmolality",
        "aliases": ["toxic alcohol conc"],
        "inputs": ["osm_gap_mOsm_kg", "alcohol_type"],
        "outputs": ["conc_mg_dL"],
        "references": [],
    },
    "calculated_urine_osmolality": {
        "domain": "osmolality",
        "aliases": ["calc urine osm"],
        "inputs": ["u_na_mEq_L", "u_k_mEq_L", "u_bun_mg_dL", "u_glucose_mg_dL"],
        "outputs": ["calc_urine_osm_mOsm_kg"],
        "references": [],
    },
    "urine_osmolal_gap": {
        "domain": "osmolality",
        "aliases": ["UOG"],
        "inputs": ["measured_u_osm_mOsm_kg", "calculated_u_osm_mOsm_kg"],
        "outputs": ["uog_mOsm_kg", "nh4_estimate"],
        "references": [],
    },
    # === Fluid & Electrolyte (3) ===
    "free_water_deficit": {
        "domain": "fluid_electrolyte",
        "aliases": ["FWD"],
        "inputs": ["sex", "age_years", "weight_kg", "na_measured_mEq_L"],
        "outputs": ["deficit_L"],
        "references": [],
    },
    "adrogue_madias": {
        "domain": "fluid_electrolyte",
        "aliases": ["Adrogue-Madias"],
        "inputs": ["na_infusate_mEq_L", "na_serum_mEq_L", "tbw_L"],
        "outputs": ["delta_na_per_L"],
        "references": ["Adrogue HJ, Madias NE. NEJM 2000;342:1581-9"],
    },
    "sodium_capping": {
        "domain": "fluid_electrolyte",
        "aliases": ["Na capping"],
        "inputs": ["na_measured_mEq_L", "lower", "upper"],
        "outputs": ["na_capped"],
        "references": [],
    },
    # === Hepatology (2) ===
    "meld_score": {
        "domain": "hepatology",
        "aliases": ["MELD"],
        "inputs": ["creatinine_mg_dL", "bilirubin_mg_dL", "inr", "on_dialysis"],
        "outputs": ["meld_score"],
        "references": ["Kamath PS et al. Hepatology 2001;33:464-70"],
    },
    "meld_na_score": {
        "domain": "hepatology",
        "aliases": ["MELD-Na", "UNOS MELD"],
        "inputs": ["meld_raw", "na_mEq_L"],
        "outputs": ["meld_na_score"],
        "references": ["Kim WR et al. Hepatology 2008;47:1363-70"],
    },
    # === Valvular (3) ===
    "gorlin_ava": {
        "domain": "valvular",
        "aliases": ["Gorlin AVA"],
        "inputs": ["co_L_min", "sep_s", "hr_bpm", "delta_p_mmHg"],
        "outputs": ["ava_cm2"],
        "references": ["Gorlin R, Gorlin SG. Am Heart J 1951;41:1-29"],
    },
    "gorlin_mva": {
        "domain": "valvular",
        "aliases": ["Gorlin MVA"],
        "inputs": ["co_L_min", "dfp_s", "hr_bpm", "delta_p_mmHg"],
        "outputs": ["mva_cm2"],
        "references": ["Gorlin R, Gorlin SG. Am Heart J 1951;41:1-29"],
    },
    "ava_index": {
        "domain": "valvular",
        "aliases": ["AVAi"],
        "inputs": ["ava_cm2", "bsa_m2"],
        "outputs": ["avai_cm2_m2"],
        "references": [],
    },
    # === Echocardiography (2) ===
    "devereux_lv_mass": {
        "domain": "echocardiography",
        "aliases": ["LVM", "Devereux LVM"],
        "inputs": ["lvedd_cm", "ivsd_cm", "pwd_cm"],
        "outputs": ["lvm_g"],
        "references": ["Devereux RB et al. Am J Cardiol 1986;57:450-8"],
    },
    "lv_mass_index": {
        "domain": "echocardiography",
        "aliases": ["LVMI"],
        "inputs": ["lvm_g", "bsa_m2"],
        "outputs": ["lvmi_g_m2"],
        "references": [],
    },
    # === Burn Management (4) ===
    "parkland_formula": {
        "domain": "burn",
        "aliases": ["Parkland"],
        "inputs": ["weight_kg", "tbsa_pct", "dose_mL_per_kg_pct"],
        "outputs": ["total_24h_mL"],
        "references": ["Baxter CR. Surg Clin North Am 1978;58:1293-312"],
    },
    "holliday_segar": {
        "domain": "burn",
        "aliases": ["4-2-1 rule"],
        "inputs": ["weight_kg"],
        "outputs": ["daily_mL", "hourly_mL"],
        "references": ["Holliday MA, Segar WE. Pediatrics 1957;19:823-32"],
    },
    "burn_fluid_timing": {
        "domain": "burn",
        "aliases": ["burn timing"],
        "inputs": ["total_24h_mL", "hours_since_burn", "prehospital_mL"],
        "outputs": ["first8h_mL", "next16h_mL", "rates"],
        "references": [],
    },
    "burn_rate_adjustment": {
        "domain": "burn",
        "aliases": ["burn rate adjustment"],
        "inputs": ["target_vol_mL", "remaining_hours", "maintenance_rate_mL_h"],
        "outputs": ["adjusted_rate_mL_h"],
        "references": [],
    },
    # === Endocrine (2) ===
    "dka_insulin_tdd": {
        "domain": "endocrine",
        "aliases": ["DKA TDD"],
        "inputs": ["iv_rate_U_h", "safety_factor"],
        "outputs": ["tdd_U"],
        "references": [],
    },
    "dka_insulin_split": {
        "domain": "endocrine",
        "aliases": ["DKA insulin split"],
        "inputs": ["tdd_U", "basal_fraction", "meals"],
        "outputs": ["basal_U", "bolus_per_meal_U"],
        "references": [],
    },
    # === Toxicology (2) ===
    "nac_three_bag": {
        "domain": "toxicology",
        "aliases": ["NAC 3-bag"],
        "inputs": ["weight_kg", "concentration_mg_mL"],
        "outputs": ["bag1/2/3 doses and volumes"],
        "references": ["Prescott LF. BMJ 1979;2:1097-100"],
    },
    "nac_two_bag": {
        "domain": "toxicology",
        "aliases": ["NAC 2-bag"],
        "inputs": ["weight_kg", "concentration_mg_mL"],
        "outputs": ["bag1/2 doses and volumes"],
        "references": [],
    },
    # === Oncology (2) ===
    "calvert_carboplatin": {
        "domain": "oncology",
        "aliases": ["Calvert"],
        "inputs": ["target_auc", "crcl_mL_min"],
        "outputs": ["dose_mg"],
        "references": ["Calvert AH et al. J Clin Oncol 1989;7:1748-56"],
    },
    "paclitaxel_dose": {
        "domain": "oncology",
        "aliases": [],
        "inputs": ["bsa_m2", "dose_mg_per_m2"],
        "outputs": ["dose_mg"],
        "references": [],
    },
    # === Neurology (3) ===
    "tpa_dose": {
        "domain": "neurology",
        "aliases": ["alteplase", "tPA"],
        "inputs": ["weight_kg"],
        "outputs": ["total_mg", "bolus_mg", "infusion_mg", "waste_mg"],
        "references": ["AHA/ASA Guidelines 2019"],
    },
    "phenytoin_loading": {
        "domain": "neurology",
        "aliases": ["phenytoin LD"],
        "inputs": ["adjbw_kg", "target_mg_per_kg"],
        "outputs": ["dose_mg"],
        "references": [],
    },
    "phenytoin_infusion_rate": {
        "domain": "neurology",
        "aliases": ["phenytoin rate"],
        "inputs": ["dose_mg", "max_rate_mg_min"],
        "outputs": ["infusion_time_min"],
        "references": [],
    },
    # === Dialysis (4) ===
    "daugirdas_ktv": {
        "domain": "dialysis",
        "aliases": ["spKt/V", "Daugirdas II"],
        "inputs": ["bun_pre_mg_dL", "bun_post_mg_dL", "t_hours", "uf_L", "v_L"],
        "outputs": ["spktv"],
        "references": ["Daugirdas JT. JASN 1993;4:1205-13"],
    },
    "residual_renal_clearance": {
        "domain": "dialysis",
        "aliases": ["KRU"],
        "inputs": ["u_urea_mg_dL", "urine_vol_mL", "collection_time_min", "p_urea_mg_dL"],
        "outputs": ["kru_mL_min"],
        "references": [],
    },
    "renal_ktv": {
        "domain": "dialysis",
        "aliases": ["renal Kt/V"],
        "inputs": ["kru_mL_min", "watson_v_L"],
        "outputs": ["daily_ktv", "weekly_ktv"],
        "references": [],
    },
    "weekly_total_ktv": {
        "domain": "dialysis",
        "aliases": ["total Kt/V"],
        "inputs": ["peritoneal_ktv_weekly", "renal_ktv_weekly"],
        "outputs": ["total_weekly_ktv"],
        "references": ["KDOQI PD Adequacy Guidelines 2006"],
    },
    # === Nutrition (4) ===
    "harris_benedict": {
        "domain": "nutrition",
        "aliases": ["BEE", "Harris-Benedict"],
        "inputs": ["sex", "weight_kg", "height_cm", "age_years"],
        "outputs": ["bee_kcal"],
        "references": ["Harris JA, Benedict FG. Carnegie Inst. 1919"],
    },
    "tpn_target_calories": {
        "domain": "nutrition",
        "aliases": ["TEE"],
        "inputs": ["bee_kcal", "stress_factor", "supply_fraction"],
        "outputs": ["tee_kcal"],
        "references": [],
    },
    "tpn_protein": {
        "domain": "nutrition",
        "aliases": ["TPN protein"],
        "inputs": ["weight_kg", "protein_g_per_kg"],
        "outputs": ["protein_g"],
        "references": [],
    },
    "tpn_osmolarity": {
        "domain": "nutrition",
        "aliases": ["TPN osm"],
        "inputs": ["glucose_g", "amino_acid_g", "lipid_g"],
        "outputs": ["osm_mOsm_L"],
        "references": [],
    },
    # === Hematology (3) ===
    "nadler_blood_volume": {
        "domain": "hematology",
        "aliases": ["Nadler TBV"],
        "inputs": ["sex", "height_m", "weight_kg"],
        "outputs": ["tbv_L"],
        "references": ["Nadler SB et al. Surgery 1962;51:224-32"],
    },
    "plasma_volume": {
        "domain": "hematology",
        "aliases": ["PV"],
        "inputs": ["tbv_L", "hct_fraction"],
        "outputs": ["pv_L"],
        "references": [],
    },
    "tpe_replacement_volume": {
        "domain": "hematology",
        "aliases": ["TPE volume", "plasma exchange volume"],
        "inputs": ["plasma_volume_L", "tpe_multiplier"],
        "outputs": ["replacement_volume_L"],
        "references": [],
    },
    # === Nuclear Medicine (3) ===
    "marinelli_i131": {
        "domain": "nuclear_medicine",
        "aliases": ["Marinelli", "I-131 activity"],
        "inputs": ["target_dose_Gy", "gland_mass_g", "raiu_fraction", "t_eff_days"],
        "outputs": ["activity_MBq", "activity_mCi"],
        "references": [],
    },
    "target_absorbed_dose": {
        "domain": "nuclear_medicine",
        "aliases": ["target dose Gy"],
        "inputs": ["treatment_goal"],
        "outputs": ["dose_Gy"],
        "references": [],
    },
    "activity_unit_conversion": {
        "domain": "nuclear_medicine",
        "aliases": ["activity conversion"],
        "inputs": ["value", "from_unit", "to_unit"],
        "outputs": ["converted_value"],
        "references": [],
    },
    # === Diuretics (1) ===
    "diuretic_ratio": {
        "domain": "diuretics",
        "aliases": ["spironolactone:furosemide ratio"],
        "inputs": ["current_spiro_mg", "current_furo_mg", "step"],
        "outputs": ["new_doses", "ratio"],
        "references": ["AASLD Practice Guidance on Ascites 2021"],
    },
}


def get_tool_ids_by_domain(domain: str) -> list[str]:
    """Return all tool IDs for a given domain."""
    return [k for k, v in FORMULA_REGISTRY.items() if v["domain"] == domain]


def get_all_domains() -> list[str]:
    """Return all unique domain names."""
    return sorted(set(v["domain"] for v in FORMULA_REGISTRY.values()))


def search_by_alias(query: str) -> list[str]:
    """Search for tools by alias (case-insensitive partial match)."""
    query_lower = query.lower()
    results = []
    for tool_id, meta in FORMULA_REGISTRY.items():
        if query_lower in tool_id.lower():
            results.append(tool_id)
            continue
        for alias in meta.get("aliases", []):
            if query_lower in alias.lower():
                results.append(tool_id)
                break
    return results
