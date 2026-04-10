"""Pydantic models for the Teloscopy web API.

Defines request/response schemas for every endpoint including user
profiles, analysis pipelines, disease-risk scoring, and diet planning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
import enum
import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    class StrEnum(str, enum.Enum):
        """Backport of StrEnum for Python < 3.11."""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Sex(StrEnum):
    """Biological sex options."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class JobStatusEnum(StrEnum):
    """Possible states for an analysis job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(StrEnum):
    """Categorical disease-risk level."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AgentStatusEnum(StrEnum):
    """Status of an individual agent in the multi-agent system."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    """Demographic and health information supplied by the user."""

    age: int = Field(..., ge=1, le=150, description="Age in years")
    sex: Sex = Field(..., description="Biological sex")
    region: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Geographic region (e.g. 'East Asia', 'Northern Europe')",
    )
    country: str | None = Field(
        None,
        max_length=128,
        description="Country (e.g. 'India', 'USA', 'Japan'). Enables country-specific diet plans.",
    )
    state: str | None = Field(
        None,
        max_length=128,
        description="State or province (e.g. 'Kerala', 'California'). Enables state-level diet personalisation.",
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Dietary restrictions such as 'vegetarian', 'gluten-free'",
    )
    known_variants: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Known genetic variants (rsIDs or gene names)",
    )


# ---------------------------------------------------------------------------
# Analysis (full pipeline)
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Request body for the full analysis endpoint.

    The microscopy image is uploaded as a multipart file, so it is *not*
    part of this schema.  This model captures the JSON metadata sent
    alongside the file.
    """

    user_profile: UserProfile


class TelomereResult(BaseModel):
    """Results from telomere image analysis."""

    mean_length: float = Field(..., description="Mean telomere length in kb")
    std_dev: float = Field(..., description="Standard deviation of length")
    t_s_ratio: float = Field(..., description="Telomere-to-single-copy gene ratio")
    biological_age_estimate: int = Field(..., description="Estimated biological age")
    overlay_image_url: str | None = Field(None, description="URL of the annotated overlay image")
    raw_measurements: list[float] = Field(
        default_factory=list,
        description="Individual telomere length measurements",
    )


class DiseaseRisk(BaseModel):
    """A single disease-risk entry."""

    disease: str
    risk_level: RiskLevel
    probability: float = Field(..., ge=0.0, le=1.0)
    contributing_factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class MealPlan(BaseModel):
    """One day's meal plan."""

    day: str
    breakfast: str
    lunch: str
    dinner: str
    snacks: list[str] = Field(default_factory=list)


class DietRecommendation(BaseModel):
    """Dietary recommendations tied to genomic / telomere findings."""

    summary: str
    key_nutrients: list[str] = Field(default_factory=list, max_length=100)
    foods_to_increase: list[str] = Field(default_factory=list, max_length=100)
    foods_to_avoid: list[str] = Field(default_factory=list, max_length=100)
    meal_plans: list[MealPlan] = Field(default_factory=list)
    calorie_target: int | None = None


class _AnalysisResponseBase(BaseModel):
    """Deprecated — replaced by AnalysisResponse with facial_analysis field."""

    pass


# ---------------------------------------------------------------------------
# Disease Risk (standalone)
# ---------------------------------------------------------------------------


class DiseaseRiskRequest(BaseModel):
    """Standalone disease-risk request (no image required)."""

    known_variants: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Genetic variants (rsIDs or gene names)",
    )
    telomere_length: float | None = Field(None, description="Mean telomere length in kb")
    age: int = Field(..., ge=1, le=150)
    sex: Sex = Field(...)
    region: str = Field(..., min_length=1, max_length=128)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "known_variants": ["rs429358:CT", "rs7412:CC", "rs1801133:AG"],
                    "telomere_length": 6.8,
                    "age": 45,
                    "sex": "female",
                    "region": "Northern Europe",
                }
            ]
        }
    }


class DiseaseRiskResponse(BaseModel):
    """Response from the standalone disease-risk endpoint."""

    risks: list[DiseaseRisk] = Field(default_factory=list)
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Composite risk score")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "substitute for professional medical advice, diagnosis, or treatment. Disease risk scores "
            "are statistical estimates from published research — not clinical diagnoses. Nutritional "
            "recommendations are general wellness guidance — not medical prescriptions. Always consult "
            "a qualified registered medical practitioner. Governed by Indian law including the Digital "
            "Personal Data Protection Act, 2023."
        ),
        description="Legal and scientific disclaimer (DPDP Act 2023, IT Act 2000, D&C Act 1940 compliant)",
    )


# ---------------------------------------------------------------------------
# Diet Plan (standalone)
# ---------------------------------------------------------------------------


class DietPlanRequest(BaseModel):
    """Standalone diet plan request."""

    age: int = Field(..., ge=1, le=150)
    sex: Sex = Field(...)
    region: str = Field(..., min_length=1, max_length=128)
    country: str | None = Field(None, max_length=128, description="Country for regional diet")
    state: str | None = Field(None, max_length=128, description="State/province for local diet")
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=100)
    known_variants: list[str] = Field(default_factory=list, max_length=100)
    telomere_length: float | None = Field(None, description="Mean telomere length in kb")
    disease_risks: list[DiseaseRisk] = Field(default_factory=list, max_length=100)
    meal_plan_days: int = Field(7, ge=1, le=30)
    calorie_target: int = Field(2000, ge=800, le=5000)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 34,
                    "sex": "male",
                    "region": "East Asia",
                    "dietary_restrictions": ["vegetarian", "gluten-free"],
                    "known_variants": ["rs1801133:AG"],
                    "telomere_length": 7.2,
                    "disease_risks": [],
                    "meal_plan_days": 7,
                    "calorie_target": 2200,
                }
            ]
        }
    }


class DietPlanResponse(BaseModel):
    """Response from the standalone diet plan endpoint."""

    recommendation: DietRecommendation
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "substitute for professional medical advice, diagnosis, or treatment. Disease risk scores "
            "are statistical estimates from published research — not clinical diagnoses. Nutritional "
            "recommendations are general wellness guidance — not medical prescriptions. Always consult "
            "a qualified registered medical practitioner. Governed by Indian law including the Digital "
            "Personal Data Protection Act, 2023."
        ),
        description="Legal and scientific disclaimer (DPDP Act 2023, IT Act 2000, D&C Act 1940 compliant)",
    )


# ---------------------------------------------------------------------------
# Job Status
# ---------------------------------------------------------------------------


class JobStatus(BaseModel):
    """Status of an asynchronous analysis job."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatusEnum = Field(default=JobStatusEnum.PENDING)
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = Field(default="Job created")
    result: AnalysisResponse | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------


class AgentInfo(BaseModel):
    """Status information for a single agent."""

    name: str
    status: AgentStatusEnum = AgentStatusEnum.IDLE
    last_active: datetime | None = None
    tasks_completed: int = 0
    current_task: str | None = None


class AgentSystemStatus(BaseModel):
    """Aggregated status of the multi-agent system."""

    agents: list[AgentInfo] = Field(default_factory=list)
    total_analyses: int = 0
    active_jobs: int = 0
    uptime_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Upload response
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response returned after a successful image upload."""

    job_id: str
    filename: str
    message: str = "Image uploaded successfully"


# ---------------------------------------------------------------------------
# Facial Analysis
# ---------------------------------------------------------------------------


class FacialMeasurementsResponse(BaseModel):
    """Facial feature measurements extracted from photograph."""

    face_width: float = 0.0
    face_height: float = 0.0
    face_ratio: float = 0.0
    skin_brightness: float = 0.0
    skin_uniformity: float = 0.0
    wrinkle_score: float = 0.0
    symmetry_score: float = 0.0
    dark_circle_score: float = 0.0
    texture_roughness: float = 0.0
    uv_damage_score: float = 0.0


class AncestryEstimateResponse(BaseModel):
    """Estimated ancestral composition from facial features."""

    european: float = 0.0
    east_asian: float = 0.0
    south_asian: float = 0.0
    african: float = 0.0
    middle_eastern: float = 0.0
    latin_american: float = 0.0
    confidence: float = 0.0


class PredictedVariantResponse(BaseModel):
    """A predicted genetic variant from facial analysis."""

    rsid: str
    gene: str
    predicted_genotype: str
    confidence: float
    basis: str
    risk_allele: str = ""
    ref_allele: str = ""


class ReconstructedSequenceResponse(BaseModel):
    """A single reconstructed DNA sequence fragment around a predicted SNP."""

    rsid: str
    gene: str
    chromosome: str
    position: int
    ref_allele: str
    predicted_allele_1: str
    predicted_allele_2: str
    flanking_5prime: str
    flanking_3prime: str
    confidence: float


class ReconstructedDNAResponse(BaseModel):
    """Reconstructed partial genome from predicted variants."""

    sequences: list[ReconstructedSequenceResponse] = Field(default_factory=list)
    total_variants: int = 0
    genome_build: str = "GRCh38/hg38"
    fasta: str = ""
    disclaimer: str = (
        "RECONSTRUCTED SEQUENCE — This is a statistical reconstruction based "
        "on facial-genomic predictions, NOT actual DNA sequencing. Predicted "
        "genotypes are derived from population-level allele frequencies and "
        "phenotypic correlations. Do not use for clinical decisions."
    )


class PharmacogenomicPredictionResponse(BaseModel):
    """A predicted pharmacogenomic interaction from facial-genomic analysis."""

    gene: str
    rsid: str
    predicted_phenotype: str
    confidence: float
    affected_drugs: list[str] = []
    clinical_recommendation: str = ""
    basis: str = ""


class FacialHealthScreeningResponse(BaseModel):
    """Health screening indicators derived from facial analysis."""

    estimated_bmi_category: str = "Unknown"
    bmi_confidence: float = 0.0
    anemia_risk_score: float = 0.0
    cardiovascular_risk_indicators: list[str] = []
    thyroid_indicators: list[str] = []
    fatigue_stress_score: float = 0.0
    hydration_score: float = 50.0


class DermatologicalAnalysisResponse(BaseModel):
    """Dermatological risk indicators from facial analysis."""

    rosacea_risk_score: float = 0.0
    melasma_risk_score: float = 0.0
    photo_aging_gap: int = 0
    acne_severity_score: float = 0.0
    skin_cancer_risk_factors: list[str] = []
    pigmentation_disorder_risk: float = 0.0
    moisture_barrier_score: float = 50.0


class ConditionScreeningResponse(BaseModel):
    """A single condition screening result from facial-genomic analysis."""

    condition: str
    risk_score: float = 0.0
    facial_markers: list[str] = []
    confidence: float = 0.0
    recommendation: str = ""


class AncestryDerivedPredictionsResponse(BaseModel):
    """Ancestry-derived metabolic and haplogroup predictions."""

    predicted_mtdna_haplogroup: str = "Unknown"
    haplogroup_confidence: float = 0.0
    lactose_tolerance_probability: float = 0.5
    alcohol_flush_probability: float = 0.0
    caffeine_sensitivity: str = "Unknown"
    bitter_taste_sensitivity: str = "Unknown"
    population_specific_risks: list[str] = []


class FacialAnalysisResult(BaseModel):
    """Complete facial-genomic analysis result."""

    image_type: str = "face_photo"
    estimated_biological_age: int = 0
    estimated_telomere_length_kb: float = 0.0
    telomere_percentile: int = 50
    skin_health_score: float = 0.0
    oxidative_stress_score: float = 0.0
    predicted_eye_colour: str = "unknown"
    predicted_hair_colour: str = "unknown"
    predicted_skin_type: str = "unknown"
    measurements: FacialMeasurementsResponse = Field(default_factory=FacialMeasurementsResponse)
    ancestry: AncestryEstimateResponse = Field(default_factory=AncestryEstimateResponse)
    predicted_variants: list[PredictedVariantResponse] = Field(default_factory=list)
    reconstructed_dna: ReconstructedDNAResponse | None = None
    pharmacogenomic_predictions: list[PharmacogenomicPredictionResponse] = []
    health_screening: FacialHealthScreeningResponse | None = None
    dermatological_analysis: DermatologicalAnalysisResponse | None = None
    condition_screenings: list[ConditionScreeningResponse] = []
    ancestry_derived: AncestryDerivedPredictionsResponse | None = None
    analysis_warnings: list[str] = Field(default_factory=list)
    # v2.1 future direction modules
    epigenetic_clock: dict | None = None
    stela_profile: dict | None = None
    cfdna_telomere: dict | None = None
    drug_targets: dict | None = None
    multi_omics: dict | None = None
    enhanced_genomic: dict | None = None


class AnalysisResponse(BaseModel):
    """Full analysis response returned once all agents have completed."""

    job_id: str
    image_type: str = Field(default="fish_microscopy", description="fish_microscopy or face_photo")
    telomere_results: TelomereResult
    disease_risks: list[DiseaseRisk] = Field(default_factory=list, max_length=100)
    diet_recommendations: DietRecommendation
    facial_analysis: FacialAnalysisResult | None = None
    report_url: str | None = None
    csv_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "substitute for professional medical advice, diagnosis, or treatment. Disease risk scores "
            "are statistical estimates from published research — not clinical diagnoses. Nutritional "
            "recommendations are general wellness guidance — not medical prescriptions. Always consult "
            "a qualified registered medical practitioner. Governed by Indian law including the Digital "
            "Personal Data Protection Act, 2023."
        ),
        description="Legal and scientific disclaimer (DPDP Act 2023, IT Act 2000, D&C Act 1940 compliant)",
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Liveness / readiness probe response."""

    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------


class ImageValidationResponse(BaseModel):
    """Result of image content validation before analysis."""

    valid: bool = True
    image_type: str = "unknown"
    width: int = 0
    height: int = 0
    channels: int = 0
    file_size_bytes: int = 0
    format_detected: str = "unknown"
    face_detected: bool = False
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal observations (e.g. extension/content format mismatch) "
            "that do not prevent the image from being used."
        ),
    )


# ---------------------------------------------------------------------------
# Profile-only analysis (no image required)
# ---------------------------------------------------------------------------


class ProfileAnalysisRequest(BaseModel):
    """Request body for analysis using only user-provided details."""

    age: int = Field(..., ge=1, le=150)
    sex: Sex = Field(...)
    region: str = Field(..., min_length=1, max_length=128)
    country: str | None = Field(None, max_length=128, description="Country for regional diet")
    state: str | None = Field(None, max_length=128, description="State/province for local diet")
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=100)
    known_variants: list[str] = Field(default_factory=list, max_length=100)
    telomere_length_kb: float | None = Field(
        None, description="Self-reported telomere length in kb (optional)"
    )
    include_nutrition: bool = Field(True, description="Include nutrition recommendations")
    include_disease_risk: bool = Field(True, description="Include disease risk assessment")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 52,
                    "sex": "female",
                    "region": "Southern Europe",
                    "dietary_restrictions": ["lactose-free"],
                    "known_variants": ["rs429358:CT", "rs7412:CC"],
                    "telomere_length_kb": 5.9,
                    "include_nutrition": True,
                    "include_disease_risk": True,
                }
            ]
        }
    }


class ProfileAnalysisResponse(BaseModel):
    """Response for profile-only analysis."""

    disease_risks: list[DiseaseRisk] = Field(default_factory=list, max_length=100)
    diet_recommendations: DietRecommendation | None = None
    overall_risk_score: float = Field(0.0, ge=0.0, le=1.0)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "substitute for professional medical advice, diagnosis, or treatment. Disease risk scores "
            "are statistical estimates from published research — not clinical diagnoses. Nutritional "
            "recommendations are general wellness guidance — not medical prescriptions. Always consult "
            "a qualified registered medical practitioner. Governed by Indian law including the Digital "
            "Personal Data Protection Act, 2023."
        ),
        description="Legal and scientific disclaimer (DPDP Act 2023, IT Act 2000, D&C Act 1940 compliant)",
    )


# ---------------------------------------------------------------------------
# Standalone nutrition request
# ---------------------------------------------------------------------------


class NutritionRequest(BaseModel):
    """Standalone nutrition/diet plan request with full user details."""

    age: int = Field(..., ge=1, le=150)
    sex: Sex = Field(...)
    region: str = Field(..., min_length=1, max_length=128)
    country: str | None = Field(None, max_length=128, description="Country for regional diet")
    state: str | None = Field(None, max_length=128, description="State/province for local diet")
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=100)
    known_variants: list[str] = Field(default_factory=list, max_length=100)
    health_conditions: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Known health conditions (e.g. 'diabetes', 'hypertension')",
    )
    calorie_target: int = Field(2000, ge=800, le=5000)
    meal_plan_days: int = Field(7, ge=1, le=30)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 29,
                    "sex": "male",
                    "region": "South Asia",
                    "dietary_restrictions": ["vegetarian"],
                    "known_variants": ["rs1801133:AG", "rs4988235:CT"],
                    "health_conditions": ["hypertension", "prediabetes"],
                    "calorie_target": 1800,
                    "meal_plan_days": 14,
                }
            ]
        }
    }


class NutritionResponse(BaseModel):
    """Response for standalone nutrition endpoint."""

    recommendation: DietRecommendation
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "substitute for professional medical advice, diagnosis, or treatment. Disease risk scores "
            "are statistical estimates from published research — not clinical diagnoses. Nutritional "
            "recommendations are general wellness guidance — not medical prescriptions. Always consult "
            "a qualified registered medical practitioner. Governed by Indian law including the Digital "
            "Personal Data Protection Act, 2023."
        ),
        description="Legal and scientific disclaimer (DPDP Act 2023, IT Act 2000, D&C Act 1940 compliant)",
    )


# ---------------------------------------------------------------------------
# Health Checkup — blood tests, urine tests, abdomen scan
# ---------------------------------------------------------------------------


class BloodTestPanel(BaseModel):
    """Structured blood test results.

    All values are optional — users submit whatever parameters they have.
    The backend interprets each provided value against age/sex ranges.
    """

    # CBC (Complete Blood Count)
    hemoglobin: float | None = Field(None, description="g/dL")
    rbc_count: float | None = Field(None, description="million cells/mcL")
    wbc_count: float | None = Field(None, description="thousand cells/mcL")
    platelet_count: float | None = Field(None, description="thousand/mcL")
    hematocrit: float | None = Field(None, description="%")
    mcv: float | None = Field(None, description="fL")
    mch: float | None = Field(None, description="pg")
    mchc: float | None = Field(None, description="g/dL")
    rdw: float | None = Field(None, description="%")
    neutrophils: float | None = Field(None, description="%")
    lymphocytes: float | None = Field(None, description="%")
    monocytes: float | None = Field(None, description="%")
    eosinophils: float | None = Field(None, description="%")
    basophils: float | None = Field(None, description="%")

    # Lipid Panel
    total_cholesterol: float | None = Field(None, description="mg/dL")
    ldl_cholesterol: float | None = Field(None, description="mg/dL")
    hdl_cholesterol: float | None = Field(None, description="mg/dL")
    triglycerides: float | None = Field(None, description="mg/dL")
    vldl: float | None = Field(None, description="mg/dL")
    total_cholesterol_hdl_ratio: float | None = Field(None, description="ratio")

    # Liver Function (LFT)
    sgot_ast: float | None = Field(None, description="U/L")
    sgpt_alt: float | None = Field(None, description="U/L")
    alkaline_phosphatase: float | None = Field(None, description="U/L")
    total_bilirubin: float | None = Field(None, description="mg/dL")
    direct_bilirubin: float | None = Field(None, description="mg/dL")
    ggt: float | None = Field(None, description="U/L")
    total_protein: float | None = Field(None, description="g/dL")
    albumin: float | None = Field(None, description="g/dL")
    globulin: float | None = Field(None, description="g/dL")
    ag_ratio: float | None = Field(None, description="ratio")

    # Kidney Function (KFT)
    blood_urea: float | None = Field(None, description="mg/dL")
    serum_creatinine: float | None = Field(None, description="mg/dL")
    uric_acid: float | None = Field(None, description="mg/dL")
    bun: float | None = Field(None, description="mg/dL")
    egfr: float | None = Field(None, description="mL/min/1.73m²")

    # Diabetes Panel
    fasting_glucose: float | None = Field(None, description="mg/dL")
    hba1c: float | None = Field(None, description="%")
    postprandial_glucose: float | None = Field(None, description="mg/dL")
    fasting_insulin: float | None = Field(None, description="µIU/mL")
    homa_ir: float | None = Field(None, description="index")

    # Thyroid
    tsh: float | None = Field(None, description="µIU/mL")
    t3: float | None = Field(None, description="ng/dL")
    t4: float | None = Field(None, description="µg/dL")
    free_t3: float | None = Field(None, description="pg/mL")
    free_t4: float | None = Field(None, description="ng/dL")

    # Vitamins
    vitamin_d: float | None = Field(None, description="ng/mL")
    vitamin_b12: float | None = Field(None, description="pg/mL")
    folate: float | None = Field(None, description="ng/mL")
    vitamin_a: float | None = Field(None, description="µg/dL")
    vitamin_e: float | None = Field(None, description="mg/L")

    # Minerals / Electrolytes
    iron: float | None = Field(None, description="µg/dL")
    ferritin: float | None = Field(None, description="ng/mL")
    tibc: float | None = Field(None, description="µg/dL")
    transferrin_saturation: float | None = Field(None, description="%")
    calcium: float | None = Field(None, description="mg/dL")
    phosphorus: float | None = Field(None, description="mg/dL")
    magnesium: float | None = Field(None, description="mg/dL")
    sodium: float | None = Field(None, description="mEq/L")
    potassium: float | None = Field(None, description="mEq/L")
    chloride: float | None = Field(None, description="mEq/L")
    zinc: float | None = Field(None, description="µg/dL")

    # Inflammation
    crp: float | None = Field(None, description="mg/L")
    esr: float | None = Field(None, description="mm/hr")
    homocysteine: float | None = Field(None, description="µmol/L")


class UrineTestPanel(BaseModel):
    """Structured urine test results."""

    ph: float | None = Field(None, description="pH units")
    specific_gravity: float | None = Field(None, description="ratio")
    protein: float | None = Field(None, description="mg/dL (0=negative)")
    glucose: float | None = Field(None, description="mg/dL (0=negative)")
    ketones: float | None = Field(None, description="mg/dL (0=negative)")
    bilirubin: float | None = Field(None, description="mg/dL (0=negative)")
    urobilinogen: float | None = Field(None, description="mg/dL")
    blood: float | None = Field(None, description="RBC/HPF (0=negative)")
    nitrites: float | None = Field(None, description="0=negative, 1=positive")
    leukocytes: float | None = Field(None, description="WBC/HPF (0=negative)")
    rbc_urine: float | None = Field(None, description="cells/HPF")
    wbc_urine: float | None = Field(None, description="cells/HPF")
    epithelial_cells: float | None = Field(None, description="cells/HPF")


class HealthCheckupRequest(BaseModel):
    """Full health checkup request with lab data, scan, and profile."""

    # User profile
    age: int = Field(..., ge=1, le=150)
    sex: Sex = Field(...)
    region: str = Field(..., min_length=1, max_length=128)
    country: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=100)
    known_variants: list[str] = Field(default_factory=list, max_length=100)

    # Lab data
    blood_tests: BloodTestPanel | None = None
    urine_tests: UrineTestPanel | None = None
    abdomen_scan_notes: str | None = Field(
        None,
        max_length=5000,
        description="Free-text abdomen scan / ultrasound findings from the doctor's report",
    )

    # Diet preferences
    calorie_target: int = Field(2000, ge=800, le=5000)
    meal_plan_days: int = Field(7, ge=1, le=30)
    health_conditions: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="User-reported health conditions (in addition to auto-detected from labs)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 42,
                    "sex": "male",
                    "region": "South Asia",
                    "country": "India",
                    "state": "Karnataka",
                    "blood_tests": {
                        "hemoglobin": 13.2,
                        "fasting_glucose": 118,
                        "hba1c": 6.1,
                        "total_cholesterol": 232,
                        "ldl_cholesterol": 155,
                        "hdl_cholesterol": 38,
                        "triglycerides": 198,
                        "vitamin_d": 14.5,
                        "vitamin_b12": 180,
                        "sgpt_alt": 52,
                        "sgot_ast": 48,
                        "crp": 4.2,
                        "tsh": 5.8,
                        "uric_acid": 8.1,
                    },
                    "urine_tests": {
                        "protein": 15,
                        "glucose": 30,
                    },
                    "abdomen_scan_notes": "Mild hepatomegaly with grade 1 fatty liver. Both kidneys normal.",
                    "calorie_target": 1800,
                    "meal_plan_days": 7,
                    "dietary_restrictions": ["vegetarian"],
                }
            ]
        }
    }


class LabResultResponse(BaseModel):
    """Single lab result in the response."""

    parameter: str
    display_name: str
    value: float
    unit: str
    status: str  # "low", "normal", "high", "critical_low", "critical_high"
    reference_low: float
    reference_high: float
    category: str


class HealthFindingResponse(BaseModel):
    """A detected health finding in the response."""

    condition: str
    display_name: str
    severity: str
    evidence: list[str]
    dietary_impact: str
    nutrients_to_increase: list[str] = Field(default_factory=list, max_length=100)
    nutrients_to_decrease: list[str] = Field(default_factory=list, max_length=100)
    foods_to_increase: list[str] = Field(default_factory=list, max_length=100)
    foods_to_avoid: list[str] = Field(default_factory=list, max_length=100)


class AbdomenFindingResponse(BaseModel):
    """Abdomen scan finding in the response."""

    organ: str
    finding: str
    severity: str
    dietary_impact: str
    foods_to_avoid: list[str] = Field(default_factory=list, max_length=100)
    foods_to_increase: list[str] = Field(default_factory=list, max_length=100)


class AyurvedicRemedyResponse(BaseModel):
    """A single Ayurvedic remedy recommendation."""

    name: str
    ingredients: list[str] = Field(default_factory=list)
    preparation: str = ""
    dosage: str = ""
    source: str = ""  # Charaka/Sushruta Samhita reference
    mechanism: str = ""
    for_conditions: list[str] = Field(default_factory=list)


class AyurvedicAnalysisResponse(BaseModel):
    """Complete Ayurvedic analysis based on Charaka & Sushruta Samhita."""

    dosha_assessment: str = ""
    remedies: list[AyurvedicRemedyResponse] = Field(default_factory=list)
    lifestyle_recommendations: list[str] = Field(default_factory=list)
    yoga_asanas: list[str] = Field(default_factory=list)
    pranayama: list[str] = Field(default_factory=list)
    dietary_principles: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default=(
            "Ayurvedic remedies are based on traditional knowledge from Charaka Samhita and "
            "Sushruta Samhita. These are for informational purposes only and should not replace "
            "professional medical advice. Consult a qualified Ayurvedic practitioner (BAMS) "
            "before starting any herbal regimen, especially if you are on allopathic medication."
        ),
    )


class HealthCheckupResponse(BaseModel):
    """Complete health checkup analysis with personalised diet plan."""

    # Lab interpretation
    lab_results: list[LabResultResponse] = Field(default_factory=list)
    abnormal_count: int = 0
    total_tested: int = 0

    # Health findings
    findings: list[HealthFindingResponse] = Field(default_factory=list)
    abdomen_findings: list[AbdomenFindingResponse] = Field(default_factory=list)
    detected_conditions: list[str] = Field(default_factory=list)

    # Health score
    overall_health_score: float = Field(0.0, ge=0.0, le=100.0)
    health_score_breakdown: dict[str, float] = Field(default_factory=dict)

    # Diet plan (reuse existing DietRecommendation)
    diet_recommendation: DietRecommendation | None = None
    dietary_modifications: list[str] = Field(default_factory=list)
    calorie_adjustment: int = 0

    # Ayurvedic remedies (Charaka & Sushruta Samhita)
    ayurvedic_analysis: AyurvedicAnalysisResponse | None = None

    # LLM-powered integrated analysis (modern + Ayurvedic)
    llm_analysis: str | None = Field(
        None,
        description=(
            "AI-generated integrated analysis combining modern clinical insights "
            "with Ayurvedic wisdom from Charaka and Sushruta Samhita. Markdown format."
        ),
    )

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: For research and educational purposes only. This is NOT a medical device, "
            "NOT registered under the Drugs & Cosmetics Act 1940 (India) or with CDSCO, and NOT a "
            "clinical establishment under the Clinical Establishments Act, 2010. Lab value interpretation "
            "is approximate and may contain OCR/parsing errors. Always verify extracted values against "
            "your original report and consult a qualified registered medical practitioner for all health "
            "decisions. Governed by Indian law including the Digital Personal Data Protection Act, 2023."
        ),
    )


# ---------------------------------------------------------------------------
# Report Upload — parse preview
# ---------------------------------------------------------------------------


class ReportParsePreview(BaseModel):
    """Preview of parsed lab values from an uploaded report.

    Returned by the ``/api/health-checkup/parse-report`` endpoint so the
    user can review and correct extracted values before running the full
    analysis.
    """

    extracted_blood_tests: dict[str, float] = Field(
        default_factory=dict,
        description="Blood test values extracted from the report, keyed by BloodTestPanel field names.",
    )
    extracted_urine_tests: dict[str, float] = Field(
        default_factory=dict,
        description="Urine test values extracted from the report, keyed by UrineTestPanel field names.",
    )
    extracted_abdomen_notes: str = Field(
        "",
        description="Abdomen/ultrasound section text extracted from the report.",
    )
    unrecognized_lines: list[str] = Field(
        default_factory=list,
        description="Lines from the report that contained numbers but could not be matched to known parameters.",
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for the extraction (0.0–1.0).",
    )
    file_type: str = Field(
        "unknown",
        description="Detected file type: 'pdf', 'image', 'text', or 'unknown'.",
    )
    text_length: int = Field(
        0,
        ge=0,
        description="Number of characters extracted from the uploaded file.",
    )


# ---------------------------------------------------------------------------
# Legal Compliance — Consent & Data Subject Rights (DPDP Act 2023)
# ---------------------------------------------------------------------------


class ConsentPurpose(StrEnum):
    """Specific purposes for which consent is collected (DPDP Act Section 5)."""
    TELOMERE_ANALYSIS = "telomere_analysis"
    DISEASE_RISK = "disease_risk"
    NUTRITION_PLAN = "nutrition_plan"
    FACIAL_ANALYSIS = "facial_analysis"
    HEALTH_REPORT = "health_report"
    GENETIC_DATA = "genetic_data"
    PROFILE_DATA = "profile_data"


class ConsentRecord(BaseModel):
    """Records explicit, informed consent per DPDP Act 2023 Section 6.
    
    Each consent record captures a Data Principal's agreement to a specific
    processing purpose, along with the version of the notice they consented to.
    """
    consent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    purpose: ConsentPurpose
    granted: bool = True
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    withdrawn_at: datetime | None = None
    notice_version: str = Field(default="1.0", description="Version of privacy notice shown at time of consent")
    ip_hash: str | None = Field(None, description="SHA-256 hash of IP for audit (not raw IP)")
    user_agent: str | None = None


class ConsentBundle(BaseModel):
    """Collection of consent records for a single session/user.
    
    Per DPDP Act Section 6, consent must be free, specific, informed, 
    unconditional, and unambiguous with a clear affirmative action.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consents: list[ConsentRecord] = Field(default_factory=list)
    data_principal_age_confirmed: bool = Field(
        False, description="User confirms they are 18+ years old (DPDP Act Section 9)"
    )
    parental_consent: bool = Field(
        False, description="Parental consent if user is under 18"
    )
    privacy_policy_version: str = "1.0"
    terms_version: str = "1.0"
    consented_at: datetime = Field(default_factory=datetime.utcnow)


class DataDeletionRequest(BaseModel):
    """Request to exercise Right to Erasure under DPDP Act 2023 Section 12(3).
    
    Since Teloscopy processes data ephemerally, this primarily serves as an
    audit record confirming the Data Principal's request was received and
    that no persistent data exists to delete.
    """
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None
    reason: str | None = Field(None, max_length=1000)
    requested_at: datetime = Field(default_factory=datetime.utcnow)


class DataDeletionResponse(BaseModel):
    """Confirmation of data deletion per DPDP Act 2023 Section 12."""
    request_id: str
    status: str = "completed"
    message: str = (
        "Teloscopy processes all data ephemerally — no personal data is "
        "stored on our servers beyond the duration of your analysis request. "
        "Any in-memory data from your session has been purged. "
        "Locally stored app preferences can be cleared from your device settings."
    )
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class GrievanceRequest(BaseModel):
    """Grievance submission per DPDP Act 2023 Section 13.
    
    The Data Fiduciary must respond within the time period prescribed
    by the Data Protection Board of India.
    """
    grievance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=5, max_length=200)
    subject: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=10, max_length=5000)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class GrievanceResponse(BaseModel):
    """Acknowledgement of grievance receipt."""
    grievance_id: str
    status: str = "received"
    message: str = (
        "Your grievance has been received. Our Grievance Officer will "
        "review and respond within 30 days as required under the "
        "Digital Personal Data Protection Act, 2023."
    )
    grievance_officer: str = "Grievance Officer, Teloscopy"
    contact_email: str = "animaticalpha123@gmail.com"
    received_at: datetime = Field(default_factory=datetime.utcnow)


class LegalNotice(BaseModel):
    """Legal notice presented to users before data collection (DPDP Act Section 5).
    
    Per Section 5(1), the Data Fiduciary must give the Data Principal a notice
    containing: (a) personal data sought and purpose, (b) how to exercise rights,
    (c) how to file complaint with the Board.
    """
    notice_version: str = "1.0"
    purposes: list[str] = Field(
        default_factory=lambda: [
            "Telomere length analysis from microscopy images",
            "Biological age estimation",
            "Disease risk assessment based on demographic and genetic data",
            "Personalised nutrition and meal plan generation",
            "Facial-genomic analysis (ancestry, skin health, pharmacogenomics)",
            "Health checkup analysis from uploaded lab reports",
        ]
    )
    data_collected: list[str] = Field(
        default_factory=lambda: [
            "Facial photographs (processed in memory, not stored)",
            "Microscopy images (processed in memory, not stored)",
            "Health reports — blood tests, urine tests, scan reports (processed in memory, not stored)",
            "Demographic information — age, sex, region, country, state",
            "Self-reported genetic variants (rsID:genotype format)",
            "Dietary restrictions and health conditions",
        ]
    )
    data_principal_rights: list[str] = Field(
        default_factory=lambda: [
            "Right to access information about processing (DPDP Act Section 11)",
            "Right to correction and erasure of personal data (DPDP Act Section 12)",
            "Right to grievance redressal (DPDP Act Section 13)",
            "Right to nominate another person to exercise rights (DPDP Act Section 14)",
            "Right to withdraw consent at any time (DPDP Act Section 6(6))",
        ]
    )
    complaint_mechanism: str = (
        "You may file a complaint with the Data Protection Board of India "
        "if you believe your rights under the Digital Personal Data "
        "Protection Act, 2023 have been violated."
    )
    grievance_officer_email: str = "animaticalpha123@gmail.com"
    medical_disclaimer: str = (
        "IMPORTANT: Teloscopy is NOT a medical device, NOT registered under the "
        "Drugs & Cosmetics Act 1940, and NOT a substitute for professional medical "
        "advice, diagnosis, or treatment. All results are for research and educational "
        "purposes only. Disease risk scores are statistical estimates, not clinical "
        "diagnoses. Nutritional recommendations are general wellness guidance, not "
        "medical prescriptions. Always consult a qualified registered medical "
        "practitioner for health decisions."
    )
