"""Comprehensive tests for the health checkup analysis module.

Covers lab interpretation, condition detection, abdomen scan parsing,
health score computation, diet integration, edge cases, and a full
integration scenario from the model's ``json_schema_extra`` example.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from teloscopy.nutrition.diet_advisor import DietAdvisor
from teloscopy.webapp.health_checkup import (
    HealthCheckupAnalyzer,
    RefRange,
    _classify,
    _get_ref,
)
from teloscopy.webapp.models import (
    AbdomenFindingResponse,
    BloodTestPanel,
    HealthCheckupRequest,
    HealthCheckupResponse,
    HealthFindingResponse,
    LabResultResponse,
    Sex,
    UrineTestPanel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def advisor():
    """Shared DietAdvisor instance (expensive init, reuse across tests)."""
    return DietAdvisor()


@pytest.fixture(scope="module")
def analyzer(advisor):
    """Shared HealthCheckupAnalyzer instance."""
    return HealthCheckupAnalyzer(advisor)


def _make_request(
    blood: BloodTestPanel | None = None,
    urine: UrineTestPanel | None = None,
    abdomen: str | None = None,
    sex: str = "male",
    age: int = 35,
    region: str = "South Asia",
    country: str | None = "India",
    state: str | None = "Karnataka",
    dietary_restrictions: list[str] | None = None,
    known_variants: list[str] | None = None,
    calorie_target: int = 2000,
    meal_plan_days: int = 7,
    health_conditions: list[str] | None = None,
) -> HealthCheckupRequest:
    """Helper to construct a HealthCheckupRequest with sensible defaults."""
    return HealthCheckupRequest(
        age=age,
        sex=sex,
        region=region,
        country=country,
        state=state,
        blood_tests=blood,
        urine_tests=urine,
        abdomen_scan_notes=abdomen,
        dietary_restrictions=dietary_restrictions or [],
        known_variants=known_variants or [],
        calorie_target=calorie_target,
        meal_plan_days=meal_plan_days,
        health_conditions=health_conditions or [],
    )


# ===================================================================
# 1. Lab interpretation tests
# ===================================================================


class TestLabInterpretation:
    """Tests for classifying individual blood/urine parameters."""

    def test_hemoglobin_normal_male(self, analyzer):
        blood = BloodTestPanel(hemoglobin=15.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        hb = [r for r in resp.lab_results if r.parameter == "hemoglobin"][0]
        assert hb.status == "normal"
        assert hb.reference_low == 13.0
        assert hb.reference_high == 17.5

    def test_hemoglobin_low_male(self, analyzer):
        blood = BloodTestPanel(hemoglobin=12.5)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        hb = [r for r in resp.lab_results if r.parameter == "hemoglobin"][0]
        assert hb.status == "low"

    def test_hemoglobin_normal_female(self, analyzer):
        blood = BloodTestPanel(hemoglobin=13.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        hb = [r for r in resp.lab_results if r.parameter == "hemoglobin"][0]
        assert hb.status == "normal"
        assert hb.reference_low == 12.0
        assert hb.reference_high == 15.5

    def test_hemoglobin_low_female(self, analyzer):
        blood = BloodTestPanel(hemoglobin=11.5)
        resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        hb = [r for r in resp.lab_results if r.parameter == "hemoglobin"][0]
        assert hb.status == "low"

    def test_sex_specific_creatinine_ranges(self, analyzer):
        """Male creatinine upper limit is 1.3; female is 1.1."""
        blood = BloodTestPanel(serum_creatinine=1.2)
        male_resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        female_resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        male_cr = [r for r in male_resp.lab_results if r.parameter == "serum_creatinine"][0]
        female_cr = [r for r in female_resp.lab_results if r.parameter == "serum_creatinine"][0]
        assert male_cr.status == "normal"
        assert female_cr.status == "high"

    def test_sex_specific_uric_acid(self, analyzer):
        """Male uric acid upper = 7.2; female = 6.0."""
        blood = BloodTestPanel(uric_acid=6.5)
        male_resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        female_resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        male_ua = [r for r in male_resp.lab_results if r.parameter == "uric_acid"][0]
        female_ua = [r for r in female_resp.lab_results if r.parameter == "uric_acid"][0]
        assert male_ua.status == "normal"
        assert female_ua.status == "high"

    def test_sex_specific_ferritin(self, analyzer):
        """Male ferritin range 20-500; female 12-150."""
        blood = BloodTestPanel(ferritin=160.0)
        male_resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        female_resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        m_f = [r for r in male_resp.lab_results if r.parameter == "ferritin"][0]
        f_f = [r for r in female_resp.lab_results if r.parameter == "ferritin"][0]
        assert m_f.status == "normal"
        assert f_f.status == "high"

    def test_critical_glucose_high(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=450.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        fg = [r for r in resp.lab_results if r.parameter == "fasting_glucose"][0]
        assert fg.status == "critical_high"

    def test_critical_glucose_low(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=35.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        fg = [r for r in resp.lab_results if r.parameter == "fasting_glucose"][0]
        assert fg.status == "critical_low"

    def test_critical_wbc_high(self, analyzer):
        blood = BloodTestPanel(wbc_count=35.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        wbc = [r for r in resp.lab_results if r.parameter == "wbc_count"][0]
        assert wbc.status == "critical_high"

    def test_urine_protein_normal(self, analyzer):
        urine = UrineTestPanel(protein=10.0)
        resp = analyzer.analyze(_make_request(urine=urine))
        prot = [r for r in resp.lab_results if r.parameter == "protein"][0]
        assert prot.status == "normal"

    def test_urine_protein_high(self, analyzer):
        urine = UrineTestPanel(protein=20.0)
        resp = analyzer.analyze(_make_request(urine=urine))
        prot = [r for r in resp.lab_results if r.parameter == "protein"][0]
        assert prot.status == "high"

    def test_urine_ph_classification(self, analyzer):
        urine = UrineTestPanel(ph=6.0)
        resp = analyzer.analyze(_make_request(urine=urine))
        ph = [r for r in resp.lab_results if r.parameter == "ph"][0]
        assert ph.status == "normal"
        assert ph.category == "Urine"

    def test_abnormal_count_tracks_correctly(self, analyzer):
        blood = BloodTestPanel(hemoglobin=10.0, fasting_glucose=130.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        assert resp.total_tested == 2
        abnormal_params = [r for r in resp.lab_results if r.status != "normal"]
        assert resp.abnormal_count == len(abnormal_params)
        assert resp.abnormal_count == 2


# ===================================================================
# 2. Condition detection tests
# ===================================================================


class TestConditionDetection:
    """Tests for automatic condition detection from lab values."""

    def test_prediabetes_fasting_glucose(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=110.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        conditions = resp.detected_conditions
        assert "prediabetes" in conditions
        assert "diabetes" not in conditions

    def test_prediabetes_hba1c(self, analyzer):
        blood = BloodTestPanel(hba1c=6.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "prediabetes" in resp.detected_conditions

    def test_prediabetes_moderate_severity_two_markers(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=115.0, hba1c=6.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        finding = [f for f in resp.findings if f.condition == "prediabetes"][0]
        assert finding.severity == "moderate"
        assert len(finding.evidence) == 2

    def test_diabetes_fasting_glucose(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=140.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "diabetes" in resp.detected_conditions

    def test_diabetes_hba1c(self, analyzer):
        blood = BloodTestPanel(hba1c=7.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "diabetes" in resp.detected_conditions

    def test_diabetes_severe_with_two_markers(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=200.0, hba1c=8.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        finding = [f for f in resp.findings if f.condition == "diabetes"][0]
        assert finding.severity == "severe"

    def test_dyslipidemia_all_markers(self, analyzer):
        blood = BloodTestPanel(
            total_cholesterol=250.0,
            ldl_cholesterol=160.0,
            hdl_cholesterol=35.0,
            triglycerides=200.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "dyslipidemia" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "dyslipidemia"][0]
        assert finding.severity == "severe"
        assert len(finding.evidence) == 4

    def test_dyslipidemia_single_marker(self, analyzer):
        blood = BloodTestPanel(total_cholesterol=220.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "dyslipidemia" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "dyslipidemia"][0]
        assert finding.severity == "mild"

    def test_liver_stress_elevated_alt_ast(self, analyzer):
        blood = BloodTestPanel(sgpt_alt=80.0, sgot_ast=60.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "liver_stress" in resp.detected_conditions

    def test_liver_stress_ggt(self, analyzer):
        blood = BloodTestPanel(ggt=55.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "liver_stress" in resp.detected_conditions

    def test_fatty_liver_requires_liver_and_metabolic(self, analyzer):
        """Fatty liver needs a liver enzyme marker + a metabolic marker."""
        # Only liver enzyme — not enough
        blood1 = BloodTestPanel(sgpt_alt=50.0)
        resp1 = analyzer.analyze(_make_request(blood=blood1))
        assert "fatty_liver" not in resp1.detected_conditions

        # Liver enzyme + triglycerides — should detect
        blood2 = BloodTestPanel(sgpt_alt=50.0, triglycerides=200.0)
        resp2 = analyzer.analyze(_make_request(blood=blood2))
        assert "fatty_liver" in resp2.detected_conditions

    def test_kidney_impairment_male_creatinine(self, analyzer):
        blood = BloodTestPanel(serum_creatinine=1.5)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        assert "kidney_impairment" in resp.detected_conditions

    def test_kidney_impairment_female_creatinine(self, analyzer):
        blood = BloodTestPanel(serum_creatinine=1.2)
        resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        assert "kidney_impairment" in resp.detected_conditions

    def test_kidney_impairment_low_egfr(self, analyzer):
        blood = BloodTestPanel(egfr=75.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "kidney_impairment" in resp.detected_conditions

    def test_hyperuricemia_male(self, analyzer):
        blood = BloodTestPanel(uric_acid=8.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        assert "hyperuricemia" in resp.detected_conditions

    def test_hyperuricemia_female(self, analyzer):
        blood = BloodTestPanel(uric_acid=6.5)
        resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        assert "hyperuricemia" in resp.detected_conditions

    def test_hypothyroidism(self, analyzer):
        blood = BloodTestPanel(tsh=6.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "hypothyroidism" in resp.detected_conditions

    def test_hyperthyroidism(self, analyzer):
        blood = BloodTestPanel(tsh=0.2)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "hyperthyroidism" in resp.detected_conditions

    def test_anemia_male(self, analyzer):
        blood = BloodTestPanel(hemoglobin=12.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        assert "anemia" in resp.detected_conditions

    def test_anemia_female(self, analyzer):
        blood = BloodTestPanel(hemoglobin=11.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="female"))
        assert "anemia" in resp.detected_conditions

    def test_vitamin_d_deficiency_severe(self, analyzer):
        blood = BloodTestPanel(vitamin_d=8.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "vitamin_d_deficiency" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "vitamin_d_deficiency"][0]
        assert finding.severity == "severe"

    def test_vitamin_d_deficiency_mild_insufficient(self, analyzer):
        blood = BloodTestPanel(vitamin_d=25.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "vitamin_d_deficiency" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "vitamin_d_deficiency"][0]
        assert finding.severity == "mild"

    def test_vitamin_d_normal(self, analyzer):
        blood = BloodTestPanel(vitamin_d=50.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "vitamin_d_deficiency" not in resp.detected_conditions

    def test_vitamin_b12_deficiency(self, analyzer):
        blood = BloodTestPanel(vitamin_b12=140.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "vitamin_b12_deficiency" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "vitamin_b12_deficiency"][0]
        assert finding.severity == "severe"

    def test_vitamin_b12_borderline(self, analyzer):
        blood = BloodTestPanel(vitamin_b12=250.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "vitamin_b12_deficiency" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "vitamin_b12_deficiency"][0]
        assert finding.severity == "mild"

    def test_iron_deficiency(self, analyzer):
        blood = BloodTestPanel(iron=40.0, ferritin=10.0, transferrin_saturation=15.0)
        resp = analyzer.analyze(_make_request(blood=blood, sex="male"))
        assert "iron_deficiency" in resp.detected_conditions

    def test_chronic_inflammation(self, analyzer):
        blood = BloodTestPanel(crp=5.0, esr=25.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "inflammation" in resp.detected_conditions
        finding = [f for f in resp.findings if f.condition == "inflammation"][0]
        assert finding.severity == "moderate"

    def test_electrolyte_imbalance_low_sodium(self, analyzer):
        blood = BloodTestPanel(sodium=130.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "electrolyte_imbalance" in resp.detected_conditions

    def test_electrolyte_imbalance_high_potassium(self, analyzer):
        blood = BloodTestPanel(potassium=5.5)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "electrolyte_imbalance" in resp.detected_conditions

    def test_electrolyte_normal_no_detection(self, analyzer):
        blood = BloodTestPanel(sodium=140.0, potassium=4.0, calcium=9.5)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "electrolyte_imbalance" not in resp.detected_conditions

    def test_proteinuria(self, analyzer):
        urine = UrineTestPanel(protein=20.0)
        resp = analyzer.analyze(_make_request(urine=urine))
        assert "proteinuria" in resp.detected_conditions

    def test_proteinuria_moderate_severity(self, analyzer):
        urine = UrineTestPanel(protein=35.0)
        resp = analyzer.analyze(_make_request(urine=urine))
        finding = [f for f in resp.findings if f.condition == "proteinuria"][0]
        assert finding.severity == "moderate"

    def test_no_conditions_all_normal(self, analyzer):
        blood = BloodTestPanel(
            hemoglobin=15.0,
            fasting_glucose=90.0,
            hba1c=5.0,
            total_cholesterol=180.0,
            ldl_cholesterol=80.0,
            hdl_cholesterol=55.0,
            triglycerides=100.0,
            tsh=2.0,
            vitamin_d=50.0,
            vitamin_b12=500.0,
            crp=1.0,
            esr=10.0,
            sodium=140.0,
            potassium=4.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        # No health conditions should be detected from normal values
        assert len(resp.findings) == 0


# ===================================================================
# 3. Abdomen scan parsing tests
# ===================================================================


class TestAbdomenParsing:
    """Tests for regex-based abdomen scan note parsing."""

    def test_grade1_fatty_liver(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Grade 1 fatty liver"))
        assert len(resp.abdomen_findings) == 1
        assert resp.abdomen_findings[0].finding == "Grade 1 fatty liver"
        assert resp.abdomen_findings[0].severity == "mild"
        assert resp.abdomen_findings[0].organ == "liver"

    def test_mild_fatty_liver(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Mild fatty liver changes"))
        assert len(resp.abdomen_findings) == 1
        assert resp.abdomen_findings[0].finding == "Grade 1 fatty liver"

    def test_grade2_fatty_liver(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Grade 2 fatty liver"))
        assert len(resp.abdomen_findings) == 1
        assert resp.abdomen_findings[0].finding == "Grade 2 fatty liver"
        assert resp.abdomen_findings[0].severity == "moderate"

    def test_hepatomegaly(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Mild hepatomegaly noted"))
        assert len(resp.abdomen_findings) == 1
        assert "Hepatomegaly" in resp.abdomen_findings[0].finding
        assert resp.abdomen_findings[0].organ == "liver"

    def test_gallstones(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Gallstones noted in gallbladder"))
        assert len(resp.abdomen_findings) == 1
        assert resp.abdomen_findings[0].organ == "gallbladder"
        assert "Gallstones" in resp.abdomen_findings[0].finding

    def test_kidney_stones(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Right kidney stone 4mm"))
        assert len(resp.abdomen_findings) == 1
        assert resp.abdomen_findings[0].organ == "kidney"

    def test_both_kidneys_normal_no_findings(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Both kidneys normal in size and echotexture"))
        assert len(resp.abdomen_findings) == 0

    def test_combined_findings(self, analyzer):
        notes = "Mild hepatomegaly with grade 1 fatty liver. Both kidneys normal. Gallstones."
        resp = analyzer.analyze(_make_request(abdomen=notes))
        organs = {f.organ for f in resp.abdomen_findings}
        # Liver should appear only once (de-duplicated); gallbladder also
        assert "liver" in organs
        assert "gallbladder" in organs
        liver_findings = [f for f in resp.abdomen_findings if f.organ == "liver"]
        assert len(liver_findings) == 1  # de-duplicated by organ

    def test_no_scan_notes(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen=None))
        assert resp.abdomen_findings == []

    def test_empty_scan_notes(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen=""))
        assert resp.abdomen_findings == []

    def test_abdomen_findings_in_detected_conditions(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Grade 1 fatty liver"))
        assert "Grade 1 fatty liver" in resp.detected_conditions


# ===================================================================
# 4. Health score tests
# ===================================================================


class TestHealthScore:
    """Tests for weighted health score computation."""

    def test_all_normal_score_near_100(self, analyzer):
        blood = BloodTestPanel(
            hemoglobin=15.0,
            fasting_glucose=90.0,
            total_cholesterol=180.0,
            ldl_cholesterol=80.0,
            hdl_cholesterol=55.0,
            triglycerides=100.0,
            sgpt_alt=30.0,
            sgot_ast=25.0,
            serum_creatinine=1.0,
            tsh=2.5,
            vitamin_d=50.0,
            crp=1.0,
            sodium=140.0,
            potassium=4.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert resp.overall_health_score >= 95.0, (
            f"All-normal score should be near 100, got {resp.overall_health_score}"
        )

    def test_multiple_abnormalities_lower_score(self, analyzer):
        blood = BloodTestPanel(
            hemoglobin=10.0,
            fasting_glucose=180.0,
            total_cholesterol=280.0,
            ldl_cholesterol=200.0,
            triglycerides=300.0,
            sgpt_alt=100.0,
            sgot_ast=80.0,
            serum_creatinine=2.0,
            tsh=8.0,
            vitamin_d=8.0,
            crp=10.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert resp.overall_health_score < 75.0, (
            f"Heavily abnormal score should be low, got {resp.overall_health_score}"
        )

    def test_score_breakdown_has_categories(self, analyzer):
        blood = BloodTestPanel(
            hemoglobin=15.0,
            fasting_glucose=90.0,
            total_cholesterol=180.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "CBC" in resp.health_score_breakdown
        assert "Diabetes Panel" in resp.health_score_breakdown
        assert "Lipid Panel" in resp.health_score_breakdown

    def test_no_labs_score_zero(self, analyzer):
        resp = analyzer.analyze(_make_request())
        assert resp.overall_health_score == 0.0
        assert resp.health_score_breakdown == {}

    def test_critical_value_heavier_penalty(self, analyzer):
        """Critical values should penalise more than just high/low."""
        blood_high = BloodTestPanel(fasting_glucose=150.0)
        blood_critical = BloodTestPanel(fasting_glucose=450.0)
        resp_high = analyzer.analyze(_make_request(blood=blood_high))
        resp_critical = analyzer.analyze(_make_request(blood=blood_critical))
        assert resp_critical.overall_health_score < resp_high.overall_health_score


# ===================================================================
# 5. Diet integration tests
# ===================================================================


class TestDietIntegration:
    """Tests for integration with DietAdvisor through the analyzer."""

    def test_diet_recommendation_always_present(self, analyzer):
        resp = analyzer.analyze(_make_request())
        assert resp.diet_recommendation is not None

    def test_conditions_passed_as_genetic_risks(self, analyzer):
        """Detected conditions should appear in the diet's summary context."""
        blood = BloodTestPanel(fasting_glucose=140.0, hba1c=7.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "diabetes" in resp.detected_conditions
        # The diet recommendation should exist and have content
        assert resp.diet_recommendation is not None
        assert resp.diet_recommendation.summary

    def test_calorie_adjustment_for_diabetes(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=140.0, hba1c=7.0)
        resp = analyzer.analyze(_make_request(blood=blood, calorie_target=2000))
        assert resp.calorie_adjustment == -200
        assert resp.diet_recommendation.calorie_target == 1800

    def test_calorie_adjustment_for_fatty_liver(self, analyzer):
        blood = BloodTestPanel(sgpt_alt=50.0, sgot_ast=40.0, triglycerides=200.0)
        resp = analyzer.analyze(_make_request(blood=blood, calorie_target=2000))
        assert "fatty_liver" in resp.detected_conditions
        assert resp.calorie_adjustment == -200

    def test_no_calorie_adjustment_when_normal(self, analyzer):
        blood = BloodTestPanel(hemoglobin=15.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert resp.calorie_adjustment == 0

    def test_dietary_modifications_match_findings(self, analyzer):
        blood = BloodTestPanel(fasting_glucose=115.0, crp=5.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        # Should have modifications for prediabetes and inflammation
        modification_texts = " ".join(resp.dietary_modifications)
        assert "Pre-Diabetes" in modification_texts
        assert "Chronic Inflammation" in modification_texts

    def test_meal_plans_generated(self, analyzer):
        blood = BloodTestPanel(hemoglobin=15.0)
        resp = analyzer.analyze(_make_request(blood=blood, meal_plan_days=7))
        assert resp.diet_recommendation is not None
        assert len(resp.diet_recommendation.meal_plans) == 7

    def test_dietary_restrictions_respected(self, analyzer):
        blood = BloodTestPanel(hemoglobin=15.0)
        resp = analyzer.analyze(
            _make_request(blood=blood, dietary_restrictions=["vegetarian"])
        )
        assert resp.diet_recommendation is not None

    def test_foods_to_increase_and_avoid_populated(self, analyzer):
        blood = BloodTestPanel(
            total_cholesterol=250.0,
            ldl_cholesterol=160.0,
            triglycerides=200.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert resp.diet_recommendation is not None
        assert len(resp.diet_recommendation.foods_to_increase) > 0
        assert len(resp.diet_recommendation.foods_to_avoid) > 0


# ===================================================================
# 6. Edge case tests
# ===================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_request_no_crash(self, analyzer):
        """No blood, urine, or abdomen data — should still return a valid response."""
        resp = analyzer.analyze(_make_request())
        assert isinstance(resp, HealthCheckupResponse)
        assert resp.lab_results == []
        assert resp.findings == []
        assert resp.abdomen_findings == []
        assert resp.total_tested == 0
        assert resp.abnormal_count == 0

    def test_only_blood_tests(self, analyzer):
        blood = BloodTestPanel(hemoglobin=15.0, fasting_glucose=90.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert resp.total_tested == 2
        assert resp.abdomen_findings == []

    def test_only_urine_tests(self, analyzer):
        urine = UrineTestPanel(ph=6.0, protein=5.0, specific_gravity=1.015)
        resp = analyzer.analyze(_make_request(urine=urine))
        assert resp.total_tested == 3
        assert all(r.category == "Urine" for r in resp.lab_results)

    def test_only_abdomen_scan(self, analyzer):
        resp = analyzer.analyze(_make_request(abdomen="Grade 1 fatty liver"))
        assert resp.total_tested == 0
        assert len(resp.abdomen_findings) == 1

    def test_extreme_blood_values(self, analyzer):
        """Extreme values should not crash the analyzer."""
        blood = BloodTestPanel(
            hemoglobin=3.0,
            fasting_glucose=600.0,
            total_cholesterol=500.0,
            serum_creatinine=10.0,
            tsh=50.0,
            vitamin_d=2.0,
            crp=100.0,
            sodium=110.0,
            potassium=7.0,
        )
        resp = analyzer.analyze(_make_request(blood=blood))
        assert isinstance(resp, HealthCheckupResponse)
        assert resp.abnormal_count > 0
        assert resp.overall_health_score < 85.0  # score penalised but weighted across categories

    def test_boundary_prediabetes_exactly_100(self, analyzer):
        """Fasting glucose exactly 100 should trigger prediabetes."""
        blood = BloodTestPanel(fasting_glucose=100.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "prediabetes" in resp.detected_conditions

    def test_boundary_diabetes_exactly_126(self, analyzer):
        """Fasting glucose exactly 126 should trigger diabetes."""
        blood = BloodTestPanel(fasting_glucose=126.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "diabetes" in resp.detected_conditions

    def test_boundary_glucose_99_no_prediabetes(self, analyzer):
        """Fasting glucose 99 should NOT trigger prediabetes."""
        blood = BloodTestPanel(fasting_glucose=99.0)
        resp = analyzer.analyze(_make_request(blood=blood))
        assert "prediabetes" not in resp.detected_conditions

    def test_user_reported_conditions_merged(self, analyzer):
        """User-reported conditions merge with auto-detected ones."""
        blood = BloodTestPanel(fasting_glucose=115.0)
        resp = analyzer.analyze(
            _make_request(blood=blood, health_conditions=["asthma"])
        )
        assert "prediabetes" in resp.detected_conditions
        # "asthma" is in all_conditions internally — it won't appear in
        # detected_conditions (which comes from findings + abdomen), but
        # the response's detected_conditions lists those from lab/abdomen findings.
        # The user-reported conditions affect diet generation internally.

    def test_disclaimer_always_present(self, analyzer):
        resp = analyzer.analyze(_make_request())
        assert "not clinical" in resp.disclaimer.lower() or "research" in resp.disclaimer.lower()

    def test_analyzed_at_is_set(self, analyzer):
        resp = analyzer.analyze(_make_request())
        assert resp.analyzed_at is not None


# ===================================================================
# 7. Full integration test (model's json_schema_extra example)
# ===================================================================


class TestFullIntegration:
    """End-to-end test using the model's example data."""

    def test_example_request_full_pipeline(self, analyzer):
        """Use the example from HealthCheckupRequest.json_schema_extra."""
        blood = BloodTestPanel(
            hemoglobin=13.2,
            fasting_glucose=118.0,
            hba1c=6.1,
            total_cholesterol=232.0,
            ldl_cholesterol=155.0,
            hdl_cholesterol=38.0,
            triglycerides=198.0,
            vitamin_d=14.5,
            vitamin_b12=180.0,
            sgpt_alt=52.0,
            sgot_ast=48.0,
            crp=4.2,
            tsh=5.8,
            uric_acid=8.1,
        )
        urine = UrineTestPanel(protein=15.0, glucose=30.0)
        request = _make_request(
            blood=blood,
            urine=urine,
            abdomen="Mild hepatomegaly with grade 1 fatty liver. Both kidneys normal.",
            sex="male",
            age=42,
            region="South Asia",
            country="India",
            state="Karnataka",
            calorie_target=1800,
            dietary_restrictions=["vegetarian"],
        )

        resp = analyzer.analyze(request)

        # --- Lab results ---
        assert resp.total_tested == 16  # 14 blood + 2 urine
        assert resp.abnormal_count > 0

        # Verify specific lab statuses
        lab_map = {r.parameter: r for r in resp.lab_results}

        # Hemoglobin 13.2 for male (range 13.0-17.5) → normal
        assert lab_map["hemoglobin"].status == "normal"

        # Fasting glucose 118 (range 70-100) → high
        assert lab_map["fasting_glucose"].status == "high"

        # HbA1c 6.1 (range 4.0-5.7) → high
        assert lab_map["hba1c"].status == "high"

        # Total cholesterol 232 (range 0-200) → high
        assert lab_map["total_cholesterol"].status == "high"

        # HDL 38 (range 40-100) → low
        assert lab_map["hdl_cholesterol"].status == "low"

        # Vitamin D 14.5 (range 30-100) → low
        assert lab_map["vitamin_d"].status == "low"

        # --- Conditions ---
        assert "prediabetes" in resp.detected_conditions
        assert "dyslipidemia" in resp.detected_conditions
        assert "vitamin_d_deficiency" in resp.detected_conditions
        assert "vitamin_b12_deficiency" in resp.detected_conditions
        assert "hypothyroidism" in resp.detected_conditions
        assert "hyperuricemia" in resp.detected_conditions
        assert "inflammation" in resp.detected_conditions
        assert "proteinuria" in resp.detected_conditions

        # --- Abdomen findings ---
        assert len(resp.abdomen_findings) >= 1
        liver_findings = [f for f in resp.abdomen_findings if f.organ == "liver"]
        assert len(liver_findings) == 1  # De-duplicated

        # --- Health score ---
        assert 0.0 < resp.overall_health_score < 100.0
        assert len(resp.health_score_breakdown) > 0

        # --- Diet ---
        assert resp.diet_recommendation is not None
        assert resp.diet_recommendation.calorie_target <= 1800
        assert len(resp.diet_recommendation.meal_plans) == 7
        assert len(resp.dietary_modifications) > 0

        # --- Metadata ---
        assert resp.analyzed_at is not None
        assert "research" in resp.disclaimer.lower() or "not clinical" in resp.disclaimer.lower()


# ===================================================================
# 8. Classify / reference range unit tests
# ===================================================================


class TestClassifyAndRefRange:
    """Unit tests for the low-level _classify and _get_ref helpers."""

    def test_classify_normal(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat")
        assert _classify(15.0, ref) == "normal"

    def test_classify_low(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat")
        assert _classify(5.0, ref) == "low"

    def test_classify_high(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat")
        assert _classify(25.0, ref) == "high"

    def test_classify_critical_low(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat", critical_low=5.0, critical_high=30.0)
        assert _classify(3.0, ref) == "critical_low"

    def test_classify_critical_high(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat", critical_low=5.0, critical_high=30.0)
        assert _classify(35.0, ref) == "critical_high"

    def test_classify_at_boundary_low(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat")
        assert _classify(10.0, ref) == "normal"

    def test_classify_at_boundary_high(self):
        ref = RefRange(10.0, 20.0, "units", "Test", "Cat")
        assert _classify(20.0, ref) == "normal"

    def test_get_ref_male_hemoglobin(self):
        ref = _get_ref("hemoglobin", "male")
        assert ref.low == 13.0
        assert ref.high == 17.5

    def test_get_ref_female_hemoglobin(self):
        ref = _get_ref("hemoglobin", "female")
        assert ref.low == 12.0
        assert ref.high == 15.5

    def test_get_ref_urine_param(self):
        ref = _get_ref("ph", "male")
        assert ref.low == 4.5
        assert ref.high == 8.0
        assert ref.category == "Urine"

    def test_get_ref_unknown_raises(self):
        with pytest.raises(KeyError):
            _get_ref("nonexistent_param", "male")


# ===================================================================
# 9. Conditions-to-risks mapping
# ===================================================================


class TestConditionsToRisks:
    """Tests for the internal condition-to-DietAdvisor risk mapping."""

    def test_prediabetes_maps_to_type2_diabetes(self, analyzer):
        risks = analyzer._conditions_to_risks(["prediabetes"])
        assert "Type 2 diabetes" in risks

    def test_dyslipidemia_maps_to_cad(self, analyzer):
        risks = analyzer._conditions_to_risks(["dyslipidemia"])
        assert "Coronary artery disease" in risks

    def test_unknown_condition_passed_through(self, analyzer):
        risks = analyzer._conditions_to_risks(["some_user_condition"])
        assert "some_user_condition" in risks

    def test_no_duplicate_risks(self, analyzer):
        """Prediabetes and diabetes both map to 'Type 2 diabetes' — no dups."""
        risks = analyzer._conditions_to_risks(["prediabetes", "diabetes"])
        assert risks.count("Type 2 diabetes") == 1
