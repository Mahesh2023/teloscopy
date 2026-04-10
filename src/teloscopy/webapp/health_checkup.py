"""Health Checkup Analysis Module.

Interprets annual health checkup lab results (blood tests, urine tests,
abdomen scan notes) to detect health conditions, compute an overall health
score, and generate a personalised diet plan that accounts for both
regional preferences and medical findings.

This module is strictly for **research / educational** purposes.
It is **not** a substitute for clinical diagnosis or medical advice.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ..nutrition.diet_advisor import DietAdvisor, DietaryRecommendation
from ..nutrition.regional_diets import resolve_region
from .models import (
    AbdomenFindingResponse,
    BloodTestPanel,
    DietRecommendation,
    HealthCheckupRequest,
    HealthCheckupResponse,
    HealthFindingResponse,
    LabResultResponse,
    MealPlan,
    UrineTestPanel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reference ranges — keyed by (sex, age_group)
# age_group: "child" (<18), "adult" (18-65), "senior" (>65)
# ---------------------------------------------------------------------------

def _age_group(age: int) -> str:
    if age < 18:
        return "child"
    if age <= 65:
        return "adult"
    return "senior"


@dataclass(frozen=True)
class RefRange:
    """Reference range for a single lab parameter."""
    low: float
    high: float
    unit: str
    display_name: str
    category: str
    critical_low: float | None = None
    critical_high: float | None = None


# Default adult reference ranges.  Sex-specific overrides follow.
_BASE_BLOOD_RANGES: dict[str, RefRange] = {
    # CBC
    "hemoglobin": RefRange(12.0, 17.5, "g/dL", "Hemoglobin", "CBC"),
    "rbc_count": RefRange(4.0, 5.9, "M cells/mcL", "RBC Count", "CBC"),
    "wbc_count": RefRange(4.0, 11.0, "K cells/mcL", "WBC Count", "CBC", critical_low=2.0, critical_high=30.0),
    "platelet_count": RefRange(150.0, 400.0, "K/mcL", "Platelet Count", "CBC", critical_low=50.0, critical_high=1000.0),
    "hematocrit": RefRange(36.0, 54.0, "%", "Hematocrit", "CBC"),
    "mcv": RefRange(80.0, 100.0, "fL", "MCV", "CBC"),
    "mch": RefRange(27.0, 33.0, "pg", "MCH", "CBC"),
    "mchc": RefRange(31.5, 35.5, "g/dL", "MCHC", "CBC"),
    "rdw": RefRange(11.5, 14.5, "%", "RDW", "CBC"),
    "neutrophils": RefRange(40.0, 70.0, "%", "Neutrophils", "CBC"),
    "lymphocytes": RefRange(20.0, 45.0, "%", "Lymphocytes", "CBC"),
    "monocytes": RefRange(2.0, 10.0, "%", "Monocytes", "CBC"),
    "eosinophils": RefRange(1.0, 6.0, "%", "Eosinophils", "CBC"),
    "basophils": RefRange(0.0, 2.0, "%", "Basophils", "CBC"),
    # Lipid Panel
    "total_cholesterol": RefRange(0.0, 200.0, "mg/dL", "Total Cholesterol", "Lipid Panel"),
    "ldl_cholesterol": RefRange(0.0, 100.0, "mg/dL", "LDL Cholesterol", "Lipid Panel"),
    "hdl_cholesterol": RefRange(40.0, 100.0, "mg/dL", "HDL Cholesterol", "Lipid Panel"),
    "triglycerides": RefRange(0.0, 150.0, "mg/dL", "Triglycerides", "Lipid Panel"),
    "vldl": RefRange(5.0, 40.0, "mg/dL", "VLDL", "Lipid Panel"),
    "total_cholesterol_hdl_ratio": RefRange(0.0, 5.0, "ratio", "TC/HDL Ratio", "Lipid Panel"),
    # LFT
    "sgot_ast": RefRange(5.0, 40.0, "U/L", "SGOT (AST)", "Liver Function"),
    "sgpt_alt": RefRange(7.0, 56.0, "U/L", "SGPT (ALT)", "Liver Function"),
    "alkaline_phosphatase": RefRange(44.0, 147.0, "U/L", "Alkaline Phosphatase", "Liver Function"),
    "total_bilirubin": RefRange(0.1, 1.2, "mg/dL", "Total Bilirubin", "Liver Function"),
    "direct_bilirubin": RefRange(0.0, 0.3, "mg/dL", "Direct Bilirubin", "Liver Function"),
    "ggt": RefRange(0.0, 45.0, "U/L", "GGT", "Liver Function"),
    "total_protein": RefRange(6.0, 8.3, "g/dL", "Total Protein", "Liver Function"),
    "albumin": RefRange(3.5, 5.5, "g/dL", "Albumin", "Liver Function"),
    "globulin": RefRange(2.0, 3.5, "g/dL", "Globulin", "Liver Function"),
    "ag_ratio": RefRange(1.0, 2.5, "ratio", "A/G Ratio", "Liver Function"),
    # KFT
    "blood_urea": RefRange(7.0, 20.0, "mg/dL", "Blood Urea", "Kidney Function"),
    "serum_creatinine": RefRange(0.6, 1.2, "mg/dL", "Serum Creatinine", "Kidney Function"),
    "uric_acid": RefRange(3.0, 7.0, "mg/dL", "Uric Acid", "Kidney Function"),
    "bun": RefRange(7.0, 20.0, "mg/dL", "BUN", "Kidney Function"),
    "egfr": RefRange(90.0, 200.0, "mL/min/1.73m²", "eGFR", "Kidney Function"),
    # Diabetes
    "fasting_glucose": RefRange(70.0, 100.0, "mg/dL", "Fasting Glucose", "Diabetes Panel", critical_low=40.0, critical_high=400.0),
    "hba1c": RefRange(4.0, 5.7, "%", "HbA1c", "Diabetes Panel"),
    "postprandial_glucose": RefRange(70.0, 140.0, "mg/dL", "Postprandial Glucose", "Diabetes Panel"),
    "fasting_insulin": RefRange(2.0, 25.0, "µIU/mL", "Fasting Insulin", "Diabetes Panel"),
    # Thyroid
    "tsh": RefRange(0.4, 4.0, "µIU/mL", "TSH", "Thyroid"),
    "t3": RefRange(80.0, 200.0, "ng/dL", "T3", "Thyroid"),
    "t4": RefRange(5.0, 12.0, "µg/dL", "T4", "Thyroid"),
    "free_t3": RefRange(2.0, 4.4, "pg/mL", "Free T3", "Thyroid"),
    "free_t4": RefRange(0.8, 1.8, "ng/dL", "Free T4", "Thyroid"),
    # Vitamins
    "vitamin_d": RefRange(30.0, 100.0, "ng/mL", "Vitamin D", "Vitamins"),
    "vitamin_b12": RefRange(200.0, 900.0, "pg/mL", "Vitamin B12", "Vitamins"),
    "folate": RefRange(3.0, 20.0, "ng/mL", "Folate", "Vitamins"),
    # Minerals / Electrolytes
    "iron": RefRange(60.0, 170.0, "µg/dL", "Iron", "Minerals"),
    "ferritin": RefRange(12.0, 300.0, "ng/mL", "Ferritin", "Minerals"),
    "tibc": RefRange(250.0, 400.0, "µg/dL", "TIBC", "Minerals"),
    "transferrin_saturation": RefRange(20.0, 50.0, "%", "Transferrin Saturation", "Minerals"),
    "calcium": RefRange(8.5, 10.5, "mg/dL", "Calcium", "Minerals", critical_low=6.0, critical_high=13.0),
    "phosphorus": RefRange(2.5, 4.5, "mg/dL", "Phosphorus", "Minerals"),
    "magnesium": RefRange(1.7, 2.2, "mg/dL", "Magnesium", "Minerals"),
    "sodium": RefRange(136.0, 145.0, "mEq/L", "Sodium", "Electrolytes", critical_low=120.0, critical_high=160.0),
    "potassium": RefRange(3.5, 5.0, "mEq/L", "Potassium", "Electrolytes", critical_low=2.5, critical_high=6.5),
    "chloride": RefRange(98.0, 106.0, "mEq/L", "Chloride", "Electrolytes"),
    # Inflammation
    "crp": RefRange(0.0, 3.0, "mg/L", "C-Reactive Protein", "Inflammation"),
    "esr": RefRange(0.0, 20.0, "mm/hr", "ESR", "Inflammation"),
    "homocysteine": RefRange(5.0, 15.0, "µmol/L", "Homocysteine", "Inflammation"),
}

# Sex-specific overrides for certain parameters.
_SEX_OVERRIDES: dict[str, dict[str, tuple[float, float]]] = {
    "hemoglobin": {"male": (13.0, 17.5), "female": (12.0, 15.5)},
    "hematocrit": {"male": (38.0, 54.0), "female": (36.0, 48.0)},
    "rbc_count": {"male": (4.5, 5.9), "female": (4.0, 5.5)},
    "ferritin": {"male": (20.0, 500.0), "female": (12.0, 150.0)},
    "iron": {"male": (65.0, 175.0), "female": (50.0, 170.0)},
    "uric_acid": {"male": (3.5, 7.2), "female": (2.5, 6.0)},
    "serum_creatinine": {"male": (0.7, 1.3), "female": (0.6, 1.1)},
    "esr": {"male": (0.0, 15.0), "female": (0.0, 20.0)},
}

# Urine reference ranges.
_URINE_RANGES: dict[str, RefRange] = {
    "ph": RefRange(4.5, 8.0, "pH", "Urine pH", "Urine"),
    "specific_gravity": RefRange(1.005, 1.030, "", "Specific Gravity", "Urine"),
    "protein": RefRange(0.0, 14.0, "mg/dL", "Urine Protein", "Urine"),
    "glucose": RefRange(0.0, 0.0, "mg/dL", "Urine Glucose", "Urine"),
    "ketones": RefRange(0.0, 0.0, "mg/dL", "Urine Ketones", "Urine"),
    "bilirubin": RefRange(0.0, 0.0, "mg/dL", "Urine Bilirubin", "Urine"),
    "urobilinogen": RefRange(0.2, 1.0, "mg/dL", "Urobilinogen", "Urine"),
    "blood": RefRange(0.0, 0.0, "RBC/HPF", "Urine Blood", "Urine"),
    "nitrites": RefRange(0.0, 0.0, "", "Nitrites", "Urine"),
    "leukocytes": RefRange(0.0, 5.0, "WBC/HPF", "Leukocytes", "Urine"),
    "rbc_urine": RefRange(0.0, 3.0, "cells/HPF", "Urine RBC", "Urine"),
    "wbc_urine": RefRange(0.0, 5.0, "cells/HPF", "Urine WBC", "Urine"),
    "epithelial_cells": RefRange(0.0, 5.0, "cells/HPF", "Epithelial Cells", "Urine"),
}


def _get_ref(param: str, sex: str) -> RefRange:
    """Get reference range with sex-specific adjustments."""
    base = _BASE_BLOOD_RANGES.get(param) or _URINE_RANGES.get(param)
    if base is None:
        raise KeyError(param)
    overrides = _SEX_OVERRIDES.get(param, {})
    if sex in overrides:
        lo, hi = overrides[sex]
        return RefRange(lo, hi, base.unit, base.display_name, base.category,
                        base.critical_low, base.critical_high)
    return base


def _classify(value: float, ref: RefRange) -> str:
    """Classify a lab value as low/normal/high/critical."""
    if ref.critical_low is not None and value < ref.critical_low:
        return "critical_low"
    if ref.critical_high is not None and value > ref.critical_high:
        return "critical_high"
    if value < ref.low:
        return "low"
    if value > ref.high:
        return "high"
    return "normal"


# ---------------------------------------------------------------------------
# Condition detection rules
# ---------------------------------------------------------------------------

@dataclass
class _ConditionRule:
    """A rule that detects a health condition from lab values."""
    condition: str
    display_name: str
    check: str  # callable name on HealthCheckupAnalyzer
    dietary_impact: str
    nutrients_to_increase: list[str] = field(default_factory=list)
    nutrients_to_decrease: list[str] = field(default_factory=list)
    foods_to_increase: list[str] = field(default_factory=list)
    foods_to_avoid: list[str] = field(default_factory=list)


_CONDITION_RULES: list[_ConditionRule] = [
    _ConditionRule(
        "prediabetes", "Pre-Diabetes", "_check_prediabetes",
        "Reduce simple carbohydrates, increase fiber and chromium",
        nutrients_to_increase=["Fiber", "Chromium", "Magnesium"],
        nutrients_to_decrease=["Simple sugars", "Refined carbs"],
        foods_to_increase=["whole grains", "leafy greens", "bitter gourd", "fenugreek", "cinnamon"],
        foods_to_avoid=["white rice (large portions)", "sugary drinks", "fruit juices", "white bread"],
    ),
    _ConditionRule(
        "diabetes", "Diabetes", "_check_diabetes",
        "Strict glycemic control; high fiber, low GI diet essential",
        nutrients_to_increase=["Fiber", "Chromium", "Alpha-lipoic acid", "Magnesium"],
        nutrients_to_decrease=["Simple sugars", "Refined carbs", "Saturated fat"],
        foods_to_increase=["oats", "barley", "bitter gourd", "fenugreek seeds", "nuts", "legumes"],
        foods_to_avoid=["white rice", "potatoes (fried)", "sugary drinks", "sweets", "white bread"],
    ),
    _ConditionRule(
        "dyslipidemia", "Dyslipidemia", "_check_dyslipidemia",
        "Reduce saturated/trans fats, increase omega-3 and soluble fiber",
        nutrients_to_increase=["Omega-3", "Soluble fiber", "Plant sterols"],
        nutrients_to_decrease=["Saturated fat", "Trans fat", "Dietary cholesterol"],
        foods_to_increase=["fatty fish", "flaxseeds", "walnuts", "oats", "olive oil", "almonds"],
        foods_to_avoid=["fried food", "red meat (excess)", "butter", "full-fat dairy", "coconut oil"],
    ),
    _ConditionRule(
        "liver_stress", "Liver Stress", "_check_liver_stress",
        "Support liver detox pathways; avoid alcohol and excess fats",
        nutrients_to_increase=["N-acetyl cysteine", "B-vitamins", "Vitamin E"],
        nutrients_to_decrease=["Alcohol", "Refined sugar", "Saturated fat"],
        foods_to_increase=["cruciferous vegetables", "turmeric", "green tea", "beets", "garlic"],
        foods_to_avoid=["alcohol", "processed foods", "fried foods", "high-sugar foods"],
    ),
    _ConditionRule(
        "fatty_liver", "Fatty Liver", "_check_fatty_liver",
        "Weight management and low-glycemic diet to reduce liver fat",
        nutrients_to_increase=["Omega-3", "Vitamin E", "Choline"],
        nutrients_to_decrease=["Fructose", "Saturated fat", "Refined carbs"],
        foods_to_increase=["fatty fish", "olive oil", "coffee", "walnuts", "avocado"],
        foods_to_avoid=["sugary drinks", "fruit juice", "white bread", "fried foods", "alcohol"],
    ),
    _ConditionRule(
        "kidney_impairment", "Kidney Impairment", "_check_kidney_impairment",
        "Moderate protein intake, limit sodium and potassium if advanced",
        nutrients_to_increase=["Omega-3"],
        nutrients_to_decrease=["Sodium", "Excess protein", "Phosphorus"],
        foods_to_increase=["cabbage", "bell peppers", "blueberries", "olive oil", "egg whites"],
        foods_to_avoid=["processed meats", "excess salt", "bananas (if potassium high)", "cola"],
    ),
    _ConditionRule(
        "hyperuricemia", "Hyperuricemia / Gout Risk", "_check_hyperuricemia",
        "Low-purine diet, increase hydration and vitamin C",
        nutrients_to_increase=["Vitamin C", "Water"],
        nutrients_to_decrease=["Purines", "Fructose", "Alcohol"],
        foods_to_increase=["cherries", "low-fat dairy", "vegetables", "whole grains"],
        foods_to_avoid=["organ meats", "shellfish", "beer", "sugary drinks", "red meat"],
    ),
    _ConditionRule(
        "hypothyroidism", "Hypothyroidism", "_check_hypothyroidism",
        "Ensure adequate iodine and selenium; limit goitrogens",
        nutrients_to_increase=["Iodine", "Selenium", "Zinc"],
        nutrients_to_decrease=["Goitrogens (raw cruciferous)"],
        foods_to_increase=["iodized salt", "seafood", "brazil nuts", "eggs", "dairy"],
        foods_to_avoid=["raw cabbage (large amounts)", "raw broccoli (excess)", "soy (excess)"],
    ),
    _ConditionRule(
        "hyperthyroidism", "Hyperthyroidism", "_check_hyperthyroidism",
        "Increase calorie and calcium intake; limit iodine",
        nutrients_to_increase=["Calcium", "Vitamin D", "Calories"],
        nutrients_to_decrease=["Iodine", "Caffeine"],
        foods_to_increase=["cruciferous vegetables", "dairy", "whole grains", "lean protein"],
        foods_to_avoid=["seaweed", "iodized salt (excess)", "caffeine"],
    ),
    _ConditionRule(
        "anemia", "Anemia", "_check_anemia",
        "Increase iron, B12, and folate; enhance iron absorption with vitamin C",
        nutrients_to_increase=["Iron", "Vitamin B12", "Folate", "Vitamin C"],
        nutrients_to_decrease=[],
        foods_to_increase=["spinach", "lentils", "red meat", "liver", "beetroot", "citrus fruits"],
        foods_to_avoid=["tea/coffee with meals (inhibits iron)", "excess calcium with iron-rich meals"],
    ),
    _ConditionRule(
        "vitamin_d_deficiency", "Vitamin D Deficiency", "_check_vitamin_d_deficiency",
        "Supplement vitamin D; increase sun exposure and dietary sources",
        nutrients_to_increase=["Vitamin D", "Calcium"],
        nutrients_to_decrease=[],
        foods_to_increase=["fatty fish", "egg yolks", "fortified milk", "mushrooms (UV-exposed)"],
        foods_to_avoid=[],
    ),
    _ConditionRule(
        "vitamin_b12_deficiency", "Vitamin B12 Deficiency", "_check_b12_deficiency",
        "Increase B12 sources; supplementation likely needed if vegetarian",
        nutrients_to_increase=["Vitamin B12"],
        nutrients_to_decrease=[],
        foods_to_increase=["meat", "fish", "eggs", "dairy", "fortified cereals"],
        foods_to_avoid=[],
    ),
    _ConditionRule(
        "iron_deficiency", "Iron Deficiency", "_check_iron_deficiency",
        "Increase heme and non-heme iron sources with vitamin C for absorption",
        nutrients_to_increase=["Iron", "Vitamin C"],
        nutrients_to_decrease=[],
        foods_to_increase=["red meat", "spinach", "lentils", "tofu", "pumpkin seeds", "citrus"],
        foods_to_avoid=["tea/coffee with iron-rich meals", "excess dairy with iron meals"],
    ),
    _ConditionRule(
        "inflammation", "Chronic Inflammation", "_check_inflammation",
        "Anti-inflammatory diet: increase omega-3, antioxidants; reduce processed foods",
        nutrients_to_increase=["Omega-3", "Curcumin", "Antioxidants"],
        nutrients_to_decrease=["Omega-6 (excess)", "Trans fat", "Refined sugar"],
        foods_to_increase=["fatty fish", "turmeric", "berries", "leafy greens", "olive oil", "nuts"],
        foods_to_avoid=["processed foods", "fried foods", "refined sugar", "red meat (excess)"],
    ),
    _ConditionRule(
        "electrolyte_imbalance", "Electrolyte Imbalance", "_check_electrolyte_imbalance",
        "Correct electrolyte levels through targeted food and hydration",
        nutrients_to_increase=[],
        nutrients_to_decrease=[],
        foods_to_increase=["bananas", "coconut water", "leafy greens", "avocado"],
        foods_to_avoid=["excess salt", "excess caffeine"],
    ),
    _ConditionRule(
        "proteinuria", "Proteinuria", "_check_proteinuria",
        "May indicate kidney stress; moderate protein, reduce sodium",
        nutrients_to_increase=["Omega-3"],
        nutrients_to_decrease=["Sodium", "Excess protein"],
        foods_to_increase=["omega-3 rich fish", "berries", "olive oil"],
        foods_to_avoid=["excess salt", "processed meats", "very high protein diets"],
    ),
]


# ---------------------------------------------------------------------------
# Abdomen scan keyword parser
# ---------------------------------------------------------------------------

_ABDOMEN_PATTERNS: list[tuple[str, dict[str, Any]]] = [
    (r"(?:grade\s*[1I]|mild)\s*fatty\s*liver", {
        "organ": "liver", "finding": "Grade 1 fatty liver", "severity": "mild",
        "dietary_impact": "Low-glycemic diet, reduce refined carbs and alcohol",
        "foods_to_avoid": ["alcohol", "sugary drinks", "fried foods", "white bread"],
        "foods_to_increase": ["coffee", "olive oil", "fatty fish", "walnuts", "green tea"],
    }),
    (r"(?:grade\s*[2II]|moderate)\s*fatty\s*liver", {
        "organ": "liver", "finding": "Grade 2 fatty liver", "severity": "moderate",
        "dietary_impact": "Mediterranean diet strongly recommended; weight loss needed",
        "foods_to_avoid": ["alcohol", "sugar", "fried foods", "processed meats", "refined grains"],
        "foods_to_increase": ["vegetables", "olive oil", "fish", "nuts", "whole grains"],
    }),
    (r"(?:grade\s*[3III]|severe)\s*fatty\s*liver", {
        "organ": "liver", "finding": "Grade 3 fatty liver", "severity": "severe",
        "dietary_impact": "Aggressive dietary intervention required; consult hepatologist",
        "foods_to_avoid": ["alcohol", "all refined sugars", "fried foods", "processed foods"],
        "foods_to_increase": ["vegetables", "lean protein", "olive oil", "whole grains"],
    }),
    (r"hepatomegaly", {
        "organ": "liver", "finding": "Hepatomegaly (enlarged liver)", "severity": "moderate",
        "dietary_impact": "Reduce liver workload; avoid hepatotoxins and excess fat",
        "foods_to_avoid": ["alcohol", "fried foods", "processed foods"],
        "foods_to_increase": ["turmeric", "garlic", "leafy greens", "beetroot"],
    }),
    (r"(?:kidney|renal)\s*(?:stone|calcul)", {
        "organ": "kidney", "finding": "Kidney stones/calculi", "severity": "moderate",
        "dietary_impact": "Increase fluid intake; adjust oxalate/calcium based on stone type",
        "foods_to_avoid": ["excess salt", "excess animal protein", "spinach (if oxalate)", "cola"],
        "foods_to_increase": ["water", "citrus fruits (lemon)", "low-oxalate vegetables"],
    }),
    (r"(?:gall|biliary)\s*(?:stone|calcul|sludge)", {
        "organ": "gallbladder", "finding": "Gallstones/sludge", "severity": "moderate",
        "dietary_impact": "Low-fat diet; avoid rapid weight loss; increase fiber",
        "foods_to_avoid": ["fried foods", "high-fat dairy", "fatty meats", "eggs (excess)"],
        "foods_to_increase": ["vegetables", "fruits", "whole grains", "lean protein"],
    }),
    (r"splenomegaly", {
        "organ": "spleen", "finding": "Splenomegaly (enlarged spleen)", "severity": "moderate",
        "dietary_impact": "Anti-inflammatory diet; ensure adequate nutrition",
        "foods_to_avoid": ["processed foods", "excess alcohol"],
        "foods_to_increase": ["leafy greens", "lean protein", "citrus fruits"],
    }),
    (r"pancrea\w*\s*(?:calcif|inflam|enlarg)", {
        "organ": "pancreas", "finding": "Pancreatic abnormality", "severity": "moderate",
        "dietary_impact": "Low-fat diet; small frequent meals; avoid alcohol",
        "foods_to_avoid": ["alcohol", "fried foods", "high-fat foods", "red meat"],
        "foods_to_increase": ["lean protein", "cooked vegetables", "whole grains"],
    }),
]


# ---------------------------------------------------------------------------
# Health score weights by category
# ---------------------------------------------------------------------------

_CATEGORY_WEIGHTS: dict[str, float] = {
    "CBC": 0.12,
    "Lipid Panel": 0.18,
    "Liver Function": 0.14,
    "Kidney Function": 0.14,
    "Diabetes Panel": 0.16,
    "Thyroid": 0.08,
    "Vitamins": 0.06,
    "Minerals": 0.04,
    "Electrolytes": 0.04,
    "Inflammation": 0.08,
    "Urine": 0.06,
}


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class HealthCheckupAnalyzer:
    """Analyze health checkup data and generate diet recommendations.

    Parameters
    ----------
    diet_advisor : DietAdvisor
        Existing DietAdvisor instance for meal plan generation.
    """

    def __init__(self, diet_advisor: DietAdvisor) -> None:
        self._advisor = diet_advisor

    # -- public API ----------------------------------------------------------

    def analyze(self, request: HealthCheckupRequest) -> HealthCheckupResponse:
        """Run full analysis pipeline and return a response."""
        sex = request.sex.value if hasattr(request.sex, "value") else str(request.sex)
        age = request.age

        # 1. Interpret lab values
        lab_results = self._interpret_labs(request.blood_tests, request.urine_tests, sex, age)

        # 2. Detect conditions
        findings = self._detect_conditions(request.blood_tests, request.urine_tests, sex, age)

        # 3. Parse abdomen scan
        abdomen_findings = self._parse_abdomen(request.abdomen_scan_notes)

        # 4. Compute health score
        abnormal = [r for r in lab_results if r.status != "normal"]
        score, breakdown = self._compute_health_score(lab_results)

        # 5. Collect all detected conditions for diet integration
        detected_conditions = [f.condition for f in findings]
        for af in abdomen_findings:
            detected_conditions.append(af.finding)
        # Merge user-reported conditions
        all_conditions = list(set(detected_conditions + request.health_conditions))

        # 6. Generate diet plan using DietAdvisor
        region_id = resolve_region(
            request.region,
            country=request.country,
            state=request.state,
        )

        diet_rec, modifications, calorie_adj = self._generate_diet(
            all_conditions=all_conditions,
            findings=findings,
            abdomen_findings=abdomen_findings,
            region=region_id,
            age=age,
            sex=sex,
            dietary_restrictions=request.dietary_restrictions,
            known_variants=request.known_variants,
            calorie_target=request.calorie_target,
            meal_plan_days=request.meal_plan_days,
        )

        return HealthCheckupResponse(
            lab_results=lab_results,
            abnormal_count=len(abnormal),
            total_tested=len(lab_results),
            findings=findings,
            abdomen_findings=abdomen_findings,
            detected_conditions=detected_conditions,
            overall_health_score=score,
            health_score_breakdown=breakdown,
            diet_recommendation=diet_rec,
            dietary_modifications=modifications,
            calorie_adjustment=calorie_adj,
        )

    # -- lab interpretation --------------------------------------------------

    def _interpret_labs(
        self,
        blood: BloodTestPanel | None,
        urine: UrineTestPanel | None,
        sex: str,
        age: int,
    ) -> list[LabResultResponse]:
        results: list[LabResultResponse] = []
        if blood is not None:
            blood_dict = blood.model_dump(exclude_none=True)
            for param, value in blood_dict.items():
                try:
                    ref = _get_ref(param, sex)
                except KeyError:
                    continue
                status = _classify(value, ref)
                results.append(LabResultResponse(
                    parameter=param,
                    display_name=ref.display_name,
                    value=value,
                    unit=ref.unit,
                    status=status,
                    reference_low=ref.low,
                    reference_high=ref.high,
                    category=ref.category,
                ))
        if urine is not None:
            urine_dict = urine.model_dump(exclude_none=True)
            for param, value in urine_dict.items():
                try:
                    ref = _get_ref(param, sex)
                except KeyError:
                    continue
                status = _classify(value, ref)
                results.append(LabResultResponse(
                    parameter=param,
                    display_name=ref.display_name,
                    value=value,
                    unit=ref.unit,
                    status=status,
                    reference_low=ref.low,
                    reference_high=ref.high,
                    category=ref.category,
                ))
        return results

    # -- condition detection -------------------------------------------------

    def _detect_conditions(
        self,
        blood: BloodTestPanel | None,
        urine: UrineTestPanel | None,
        sex: str,
        age: int,
    ) -> list[HealthFindingResponse]:
        findings: list[HealthFindingResponse] = []
        for rule in _CONDITION_RULES:
            check_method = getattr(self, rule.check, None)
            if check_method is None:
                logger.warning("Unknown check method: %s", rule.check)
                continue
            result = check_method(blood, urine, sex, age)
            if result is not None:
                severity, evidence = result
                findings.append(HealthFindingResponse(
                    condition=rule.condition,
                    display_name=rule.display_name,
                    severity=severity,
                    evidence=evidence,
                    dietary_impact=rule.dietary_impact,
                    nutrients_to_increase=rule.nutrients_to_increase,
                    nutrients_to_decrease=rule.nutrients_to_decrease,
                    foods_to_increase=rule.foods_to_increase,
                    foods_to_avoid=rule.foods_to_avoid,
                ))
        return findings

    # -- individual condition checks (return (severity, evidence) or None) ---

    def _check_prediabetes(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.fasting_glucose is not None and 100 <= blood.fasting_glucose < 126:
            evidence.append(f"Fasting glucose {blood.fasting_glucose} mg/dL (100-125 = pre-diabetic)")
        if blood.hba1c is not None and 5.7 <= blood.hba1c < 6.5:
            evidence.append(f"HbA1c {blood.hba1c}% (5.7-6.4 = pre-diabetic)")
        if blood.postprandial_glucose is not None and 140 <= blood.postprandial_glucose < 200:
            evidence.append(f"PP glucose {blood.postprandial_glucose} mg/dL (140-199 = IGT)")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_diabetes(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.fasting_glucose is not None and blood.fasting_glucose >= 126:
            evidence.append(f"Fasting glucose {blood.fasting_glucose} mg/dL (≥126 = diabetic)")
        if blood.hba1c is not None and blood.hba1c >= 6.5:
            evidence.append(f"HbA1c {blood.hba1c}% (≥6.5 = diabetic)")
        if blood.postprandial_glucose is not None and blood.postprandial_glucose >= 200:
            evidence.append(f"PP glucose {blood.postprandial_glucose} mg/dL (≥200 = diabetic)")
        if not evidence:
            return None
        severity = "severe" if len(evidence) >= 2 else "moderate"
        return severity, evidence

    def _check_dyslipidemia(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.total_cholesterol is not None and blood.total_cholesterol > 200:
            evidence.append(f"Total cholesterol {blood.total_cholesterol} mg/dL (>200)")
        if blood.ldl_cholesterol is not None and blood.ldl_cholesterol > 100:
            lvl = "borderline" if blood.ldl_cholesterol < 160 else "high"
            evidence.append(f"LDL {blood.ldl_cholesterol} mg/dL ({lvl})")
        if blood.hdl_cholesterol is not None and blood.hdl_cholesterol < 40:
            evidence.append(f"HDL {blood.hdl_cholesterol} mg/dL (low <40)")
        if blood.triglycerides is not None and blood.triglycerides > 150:
            evidence.append(f"Triglycerides {blood.triglycerides} mg/dL (>150)")
        if not evidence:
            return None
        severity = "severe" if len(evidence) >= 3 else ("moderate" if len(evidence) >= 2 else "mild")
        return severity, evidence

    def _check_liver_stress(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.sgpt_alt is not None and blood.sgpt_alt > 56:
            evidence.append(f"ALT {blood.sgpt_alt} U/L (>56)")
        if blood.sgot_ast is not None and blood.sgot_ast > 40:
            evidence.append(f"AST {blood.sgot_ast} U/L (>40)")
        if blood.ggt is not None and blood.ggt > 45:
            evidence.append(f"GGT {blood.ggt} U/L (>45)")
        if blood.alkaline_phosphatase is not None and blood.alkaline_phosphatase > 147:
            evidence.append(f"ALP {blood.alkaline_phosphatase} U/L (>147)")
        if blood.total_bilirubin is not None and blood.total_bilirubin > 1.2:
            evidence.append(f"Total bilirubin {blood.total_bilirubin} mg/dL (>1.2)")
        if not evidence:
            return None
        severity = "severe" if len(evidence) >= 3 else ("moderate" if len(evidence) >= 2 else "mild")
        return severity, evidence

    def _check_fatty_liver(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        # Fatty liver indicated by elevated liver enzymes + high triglycerides
        evidence = []
        alt_high = blood.sgpt_alt is not None and blood.sgpt_alt > 40
        ast_high = blood.sgot_ast is not None and blood.sgot_ast > 35
        tg_high = blood.triglycerides is not None and blood.triglycerides > 150
        ggt_high = blood.ggt is not None and blood.ggt > 45
        if alt_high:
            evidence.append(f"ALT {blood.sgpt_alt} U/L (elevated)")
        if ast_high:
            evidence.append(f"AST {blood.sgot_ast} U/L (elevated)")
        if tg_high:
            evidence.append(f"Triglycerides {blood.triglycerides} mg/dL (elevated)")
        if ggt_high:
            evidence.append(f"GGT {blood.ggt} U/L (elevated)")
        # Need at least liver enzyme + one other marker
        liver_marker = alt_high or ast_high
        metabolic_marker = tg_high or ggt_high
        if not (liver_marker and metabolic_marker):
            return None
        severity = "moderate" if len(evidence) >= 3 else "mild"
        return severity, evidence

    def _check_kidney_impairment(
        self, blood: BloodTestPanel | None, urine: UrineTestPanel | None, sex: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        evidence = []
        if blood is not None:
            creat_limit = 1.3 if sex == "male" else 1.1
            if blood.serum_creatinine is not None and blood.serum_creatinine > creat_limit:
                evidence.append(f"Creatinine {blood.serum_creatinine} mg/dL (>{creat_limit})")
            if blood.egfr is not None and blood.egfr < 90:
                evidence.append(f"eGFR {blood.egfr} mL/min (< 90)")
            if blood.bun is not None and blood.bun > 20:
                evidence.append(f"BUN {blood.bun} mg/dL (>20)")
            if blood.blood_urea is not None and blood.blood_urea > 20:
                evidence.append(f"Blood urea {blood.blood_urea} mg/dL (>20)")
        if urine is not None:
            if urine.protein is not None and urine.protein > 14:
                evidence.append(f"Urine protein {urine.protein} mg/dL (positive)")
        if not evidence:
            return None
        severity = "severe" if len(evidence) >= 3 else ("moderate" if len(evidence) >= 2 else "mild")
        return severity, evidence

    def _check_hyperuricemia(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, sex: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None or blood.uric_acid is None:
            return None
        limit = 7.2 if sex == "male" else 6.0
        if blood.uric_acid > limit:
            severity = "moderate" if blood.uric_acid > limit + 1.5 else "mild"
            return severity, [f"Uric acid {blood.uric_acid} mg/dL (>{limit})"]
        return None

    def _check_hypothyroidism(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.tsh is not None and blood.tsh > 4.0:
            evidence.append(f"TSH {blood.tsh} µIU/mL (>4.0)")
        if blood.free_t4 is not None and blood.free_t4 < 0.8:
            evidence.append(f"Free T4 {blood.free_t4} ng/dL (<0.8)")
        if blood.free_t3 is not None and blood.free_t3 < 2.0:
            evidence.append(f"Free T3 {blood.free_t3} pg/mL (<2.0)")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_hyperthyroidism(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.tsh is not None and blood.tsh < 0.4:
            evidence.append(f"TSH {blood.tsh} µIU/mL (<0.4)")
        if blood.free_t4 is not None and blood.free_t4 > 1.8:
            evidence.append(f"Free T4 {blood.free_t4} ng/dL (>1.8)")
        if blood.free_t3 is not None and blood.free_t3 > 4.4:
            evidence.append(f"Free T3 {blood.free_t3} pg/mL (>4.4)")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_anemia(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, sex: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        hb_limit = 13.0 if sex == "male" else 12.0
        if blood.hemoglobin is not None and blood.hemoglobin < hb_limit:
            evidence.append(f"Hemoglobin {blood.hemoglobin} g/dL (<{hb_limit})")
        if blood.hematocrit is not None:
            hct_limit = 38.0 if sex == "male" else 36.0
            if blood.hematocrit < hct_limit:
                evidence.append(f"Hematocrit {blood.hematocrit}% (<{hct_limit})")
        if blood.mcv is not None and blood.mcv < 80:
            evidence.append(f"MCV {blood.mcv} fL (<80, microcytic)")
        if blood.ferritin is not None:
            ferr_limit = 20.0 if sex == "male" else 12.0
            if blood.ferritin < ferr_limit:
                evidence.append(f"Ferritin {blood.ferritin} ng/mL (<{ferr_limit})")
        if not evidence:
            return None
        severity = "severe" if len(evidence) >= 3 else ("moderate" if len(evidence) >= 2 else "mild")
        return severity, evidence

    def _check_vitamin_d_deficiency(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None or blood.vitamin_d is None:
            return None
        if blood.vitamin_d < 20:
            return "severe" if blood.vitamin_d < 10 else "moderate", [
                f"Vitamin D {blood.vitamin_d} ng/mL (<20 = deficient)"
            ]
        if blood.vitamin_d < 30:
            return "mild", [f"Vitamin D {blood.vitamin_d} ng/mL (20-29 = insufficient)"]
        return None

    def _check_b12_deficiency(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None or blood.vitamin_b12 is None:
            return None
        if blood.vitamin_b12 < 200:
            severity = "severe" if blood.vitamin_b12 < 150 else "moderate"
            return severity, [f"Vitamin B12 {blood.vitamin_b12} pg/mL (<200 = deficient)"]
        if blood.vitamin_b12 < 300:
            return "mild", [f"Vitamin B12 {blood.vitamin_b12} pg/mL (200-300 = borderline)"]
        return None

    def _check_iron_deficiency(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, sex: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.iron is not None:
            limit = 65.0 if sex == "male" else 50.0
            if blood.iron < limit:
                evidence.append(f"Serum iron {blood.iron} µg/dL (<{limit})")
        if blood.ferritin is not None:
            limit = 20.0 if sex == "male" else 12.0
            if blood.ferritin < limit:
                evidence.append(f"Ferritin {blood.ferritin} ng/mL (<{limit})")
        if blood.transferrin_saturation is not None and blood.transferrin_saturation < 20:
            evidence.append(f"Transferrin sat {blood.transferrin_saturation}% (<20)")
        if blood.tibc is not None and blood.tibc > 400:
            evidence.append(f"TIBC {blood.tibc} µg/dL (>400 = iron deficiency)")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_inflammation(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.crp is not None and blood.crp > 3.0:
            evidence.append(f"CRP {blood.crp} mg/L (>3.0)")
        if blood.esr is not None and blood.esr > 20:
            evidence.append(f"ESR {blood.esr} mm/hr (>20)")
        if blood.homocysteine is not None and blood.homocysteine > 15:
            evidence.append(f"Homocysteine {blood.homocysteine} µmol/L (>15)")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_electrolyte_imbalance(
        self, blood: BloodTestPanel | None, _u: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if blood is None:
            return None
        evidence = []
        if blood.sodium is not None and (blood.sodium < 136 or blood.sodium > 145):
            status = "low" if blood.sodium < 136 else "high"
            evidence.append(f"Sodium {blood.sodium} mEq/L ({status})")
        if blood.potassium is not None and (blood.potassium < 3.5 or blood.potassium > 5.0):
            status = "low" if blood.potassium < 3.5 else "high"
            evidence.append(f"Potassium {blood.potassium} mEq/L ({status})")
        if blood.chloride is not None and (blood.chloride < 98 or blood.chloride > 106):
            status = "low" if blood.chloride < 98 else "high"
            evidence.append(f"Chloride {blood.chloride} mEq/L ({status})")
        if blood.calcium is not None and (blood.calcium < 8.5 or blood.calcium > 10.5):
            status = "low" if blood.calcium < 8.5 else "high"
            evidence.append(f"Calcium {blood.calcium} mg/dL ({status})")
        if blood.magnesium is not None and (blood.magnesium < 1.7 or blood.magnesium > 2.2):
            status = "low" if blood.magnesium < 1.7 else "high"
            evidence.append(f"Magnesium {blood.magnesium} mg/dL ({status})")
        if not evidence:
            return None
        severity = "moderate" if len(evidence) >= 2 else "mild"
        return severity, evidence

    def _check_proteinuria(
        self, _blood: BloodTestPanel | None, urine: UrineTestPanel | None, _s: str, _a: int,
    ) -> tuple[str, list[str]] | None:
        if urine is None:
            return None
        evidence = []
        if urine.protein is not None and urine.protein > 14:
            evidence.append(f"Urine protein {urine.protein} mg/dL (positive)")
        if not evidence:
            return None
        severity = "moderate" if urine.protein is not None and urine.protein > 30 else "mild"
        return severity, evidence

    # -- abdomen scan parsing ------------------------------------------------

    def _parse_abdomen(self, notes: str | None) -> list[AbdomenFindingResponse]:
        if not notes:
            return []
        findings: list[AbdomenFindingResponse] = []
        text = notes.lower()
        seen_organs: set[str] = set()
        for pattern, info in _ABDOMEN_PATTERNS:
            if re.search(pattern, text):
                organ = info["organ"]
                # Avoid duplicate findings for the same organ
                if organ in seen_organs:
                    continue
                seen_organs.add(organ)
                findings.append(AbdomenFindingResponse(
                    organ=info["organ"],
                    finding=info["finding"],
                    severity=info["severity"],
                    dietary_impact=info["dietary_impact"],
                    foods_to_avoid=info.get("foods_to_avoid", []),
                    foods_to_increase=info.get("foods_to_increase", []),
                ))
        return findings

    # -- health score --------------------------------------------------------

    def _compute_health_score(
        self, lab_results: list[LabResultResponse],
    ) -> tuple[float, dict[str, float]]:
        """Compute overall health score (0–100) from lab results.

        Each tested category starts at 100 and is penalised for abnormal values.
        Categories are then weighted to produce the final score.
        """
        if not lab_results:
            return 0.0, {}

        # Group results by category
        by_cat: dict[str, list[LabResultResponse]] = {}
        for r in lab_results:
            by_cat.setdefault(r.category, []).append(r)

        breakdown: dict[str, float] = {}
        total_weight = 0.0
        weighted_sum = 0.0

        for cat, results in by_cat.items():
            cat_score = 100.0
            for r in results:
                if r.status == "critical_low" or r.status == "critical_high":
                    cat_score -= 25.0
                elif r.status == "high" or r.status == "low":
                    # Penalise proportionally to how far out of range
                    if r.status == "high" and r.reference_high > 0:
                        deviation = (r.value - r.reference_high) / r.reference_high
                    elif r.status == "low" and r.reference_low > 0:
                        deviation = (r.reference_low - r.value) / r.reference_low
                    else:
                        deviation = 0.1
                    penalty = min(20.0, max(5.0, deviation * 50.0))
                    cat_score -= penalty

            cat_score = max(0.0, min(100.0, cat_score))
            breakdown[cat] = round(cat_score, 1)
            weight = _CATEGORY_WEIGHTS.get(cat, 0.05)
            total_weight += weight
            weighted_sum += weight * cat_score

        if total_weight == 0:
            return 0.0, breakdown

        overall = round(weighted_sum / total_weight, 1)
        return overall, breakdown

    # -- diet generation -----------------------------------------------------

    def _generate_diet(
        self,
        all_conditions: list[str],
        findings: list[HealthFindingResponse],
        abdomen_findings: list[AbdomenFindingResponse],
        region: str,
        age: int,
        sex: str,
        dietary_restrictions: list[str],
        known_variants: list[str],
        calorie_target: int,
        meal_plan_days: int,
    ) -> tuple[DietRecommendation | None, list[str], int]:
        """Generate diet plan integrating health findings with DietAdvisor."""
        # Map health conditions to genetic_risks for DietAdvisor
        genetic_risks = self._conditions_to_risks(all_conditions)

        # Build variant dict from known_variants (list of rsids)
        variants: dict[str, str] = {}
        for v in known_variants:
            # Accept "rs12345:CT" or just "rs12345"
            if ":" in v:
                rsid, geno = v.split(":", 1)
                variants[rsid.strip()] = geno.strip()
            else:
                variants[v.strip()] = "unknown"

        try:
            recommendations = self._advisor.generate_recommendations(
                genetic_risks=genetic_risks,
                variants=variants,
                region=region,
                age=age,
                sex=sex,
                dietary_restrictions=dietary_restrictions,
            )

            meal_plans = self._advisor.create_meal_plan(
                recommendations=recommendations,
                region=region,
                calories=calorie_target,
                days=meal_plan_days,
                dietary_restrictions=dietary_restrictions,
            )

            if dietary_restrictions:
                meal_plans = self._advisor.adapt_to_restrictions(meal_plans, dietary_restrictions)

        except Exception:
            logger.exception("DietAdvisor failed; falling back to summary-only")
            recommendations = []
            meal_plans = []

        # Build modifications list from findings
        modifications: list[str] = []
        all_increase: list[str] = []
        all_avoid: list[str] = []

        for f in findings:
            modifications.append(f"{f.display_name}: {f.dietary_impact}")
            all_increase.extend(f.foods_to_increase)
            all_avoid.extend(f.foods_to_avoid)

        for af in abdomen_findings:
            modifications.append(f"{af.finding}: {af.dietary_impact}")
            all_increase.extend(af.foods_to_increase)
            all_avoid.extend(af.foods_to_avoid)

        # Calorie adjustment based on conditions
        calorie_adj = 0
        fatty_liver = any(f.condition == "fatty_liver" for f in findings)
        diabetes = any(f.condition == "diabetes" for f in findings)
        if fatty_liver or diabetes:
            calorie_adj = -200  # Reduce by 200 kcal

        # Build the summary
        summary_parts = []
        if findings:
            summary_parts.append(
                f"Based on {len(findings)} detected health finding(s), "
                f"your diet plan has been personalised."
            )
        if recommendations:
            top_nutrients = [r.nutrient for r in recommendations[:5]]
            summary_parts.append(f"Key nutrients: {', '.join(top_nutrients)}.")
        if not summary_parts:
            summary_parts.append("Standard balanced diet recommended for your region and profile.")

        # Deduplicate food lists
        unique_increase = list(dict.fromkeys(all_increase))
        unique_avoid = list(dict.fromkeys(all_avoid))

        # Build key nutrients from recommendations
        key_nutrients = [r.nutrient for r in recommendations[:10]]

        # Convert DietAdvisor MealPlan dataclasses to Pydantic MealPlan models.
        # Pydantic MealPlan: day(str), breakfast(str), lunch(str), dinner(str), snacks(list[str])
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pydantic_meals: list[MealPlan] = []
        for mp in meal_plans:
            def _meal_str(items: list) -> str:
                return ", ".join(f"{fi.name} ({g:.0f}g)" for fi, g in items[:4]) or "Seasonal selection"

            if isinstance(mp.day, int):
                week_num = (mp.day - 1) // 7 + 1
                day_label = day_names[(mp.day - 1) % 7]
                label = f"Week {week_num} — {day_label}" if len(meal_plans) > 7 else day_label
            else:
                label = str(mp.day)

            pydantic_meals.append(MealPlan(
                day=label,
                breakfast=_meal_str(mp.breakfast),
                lunch=_meal_str(mp.lunch),
                dinner=_meal_str(mp.dinner),
                snacks=[_meal_str(mp.snacks)] if mp.snacks else [],
            ))

        diet_rec = DietRecommendation(
            summary=" ".join(summary_parts),
            key_nutrients=key_nutrients,
            foods_to_increase=unique_increase[:20],
            foods_to_avoid=unique_avoid[:20],
            meal_plans=pydantic_meals,
            calorie_target=calorie_target + calorie_adj,
        )

        return diet_rec, modifications, calorie_adj

    def _conditions_to_risks(self, conditions: list[str]) -> list[str]:
        """Map detected conditions to risk names the DietAdvisor understands."""
        mapping: dict[str, str] = {
            "prediabetes": "Type 2 diabetes",
            "diabetes": "Type 2 diabetes",
            "dyslipidemia": "Coronary artery disease",
            "liver_stress": "Liver disease",
            "fatty_liver": "Non-alcoholic fatty liver disease",
            "kidney_impairment": "Chronic kidney disease",
            "hyperuricemia": "Gout",
            "hypothyroidism": "Hypothyroidism",
            "hyperthyroidism": "Hyperthyroidism",
            "anemia": "Iron-deficiency anemia",
            "vitamin_d_deficiency": "Osteoporosis",
            "vitamin_b12_deficiency": "Megaloblastic anemia",
            "iron_deficiency": "Iron-deficiency anemia",
            "inflammation": "Chronic inflammation",
            "electrolyte_imbalance": "Electrolyte disorder",
            "proteinuria": "Chronic kidney disease",
        }
        risks = []
        for cond in conditions:
            risk = mapping.get(cond)
            if risk and risk not in risks:
                risks.append(risk)
            elif cond not in mapping:
                # Pass through user-reported conditions as-is
                if cond not in risks:
                    risks.append(cond)
        return risks
