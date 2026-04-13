package com.teloscopy.app.data.api

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// ---------------------------------------------------------------------------
// Telomere Results
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class TelomereResult(
    @Json(name = "mean_length") val meanLength: Double,
    @Json(name = "std_dev") val stdDev: Double,
    @Json(name = "t_s_ratio") val tsRatio: Double,
    @Json(name = "biological_age_estimate") val biologicalAgeEstimate: Int,
    @Json(name = "overlay_image_url") val overlayImageUrl: String? = null,
    @Json(name = "raw_measurements") val rawMeasurements: List<Double> = emptyList()
)

// ---------------------------------------------------------------------------
// Disease Risk
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class DiseaseRisk(
    @Json(name = "disease") val disease: String,
    @Json(name = "risk_level") val riskLevel: String,
    @Json(name = "probability") val probability: Double,
    @Json(name = "contributing_factors") val contributingFactors: List<String> = emptyList(),
    @Json(name = "recommendations") val recommendations: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Diet / Nutrition
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class MealPlan(
    @Json(name = "day") val day: String,
    @Json(name = "breakfast") val breakfast: String,
    @Json(name = "lunch") val lunch: String,
    @Json(name = "dinner") val dinner: String,
    @Json(name = "snacks") val snacks: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class DietRecommendation(
    @Json(name = "summary") val summary: String,
    @Json(name = "key_nutrients") val keyNutrients: List<String> = emptyList(),
    @Json(name = "foods_to_increase") val foodsToIncrease: List<String> = emptyList(),
    @Json(name = "foods_to_avoid") val foodsToAvoid: List<String> = emptyList(),
    @Json(name = "meal_plans") val mealPlans: List<MealPlan> = emptyList(),
    @Json(name = "calorie_target") val calorieTarget: Int? = null
)

// ---------------------------------------------------------------------------
// Facial Analysis
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class FacialMeasurementsResponse(
    @Json(name = "face_width") val faceWidth: Double = 0.0,
    @Json(name = "face_height") val faceHeight: Double = 0.0,
    @Json(name = "face_ratio") val faceRatio: Double = 0.0,
    @Json(name = "skin_brightness") val skinBrightness: Double = 0.0,
    @Json(name = "skin_uniformity") val skinUniformity: Double = 0.0,
    @Json(name = "wrinkle_score") val wrinkleScore: Double = 0.0,
    @Json(name = "symmetry_score") val symmetryScore: Double = 0.0,
    @Json(name = "dark_circle_score") val darkCircleScore: Double = 0.0,
    @Json(name = "texture_roughness") val textureRoughness: Double = 0.0,
    @Json(name = "uv_damage_score") val uvDamageScore: Double = 0.0
)

@JsonClass(generateAdapter = true)
data class AncestryEstimateResponse(
    @Json(name = "european") val european: Double = 0.0,
    @Json(name = "east_asian") val eastAsian: Double = 0.0,
    @Json(name = "south_asian") val southAsian: Double = 0.0,
    @Json(name = "african") val african: Double = 0.0,
    @Json(name = "middle_eastern") val middleEastern: Double = 0.0,
    @Json(name = "latin_american") val latinAmerican: Double = 0.0,
    @Json(name = "confidence") val confidence: Double = 0.0
)

@JsonClass(generateAdapter = true)
data class PredictedVariantResponse(
    @Json(name = "rsid") val rsid: String,
    @Json(name = "gene") val gene: String,
    @Json(name = "predicted_genotype") val predictedGenotype: String,
    @Json(name = "confidence") val confidence: Double,
    @Json(name = "basis") val basis: String,
    @Json(name = "risk_allele") val riskAllele: String = "",
    @Json(name = "ref_allele") val refAllele: String = ""
)

@JsonClass(generateAdapter = true)
data class ReconstructedSequenceResponse(
    @Json(name = "rsid") val rsid: String,
    @Json(name = "gene") val gene: String,
    @Json(name = "chromosome") val chromosome: String,
    @Json(name = "position") val position: Long,
    @Json(name = "ref_allele") val refAllele: String,
    @Json(name = "predicted_allele_1") val predictedAllele1: String,
    @Json(name = "predicted_allele_2") val predictedAllele2: String,
    @Json(name = "flanking_5prime") val flanking5prime: String = "",
    @Json(name = "flanking_3prime") val flanking3prime: String = "",
    @Json(name = "confidence") val confidence: Double = 0.0
)

@JsonClass(generateAdapter = true)
data class ReconstructedDNAResponse(
    @Json(name = "sequences") val sequences: List<ReconstructedSequenceResponse> = emptyList(),
    @Json(name = "total_variants") val totalVariants: Int = 0,
    @Json(name = "genome_build") val genomeBuild: String = "GRCh38/hg38",
    @Json(name = "fasta") val fasta: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

@JsonClass(generateAdapter = true)
data class PharmacogenomicPredictionResponse(
    @Json(name = "gene") val gene: String = "",
    @Json(name = "rsid") val rsid: String = "",
    @Json(name = "predicted_phenotype") val predictedPhenotype: String = "",
    @Json(name = "confidence") val confidence: Double = 0.0,
    @Json(name = "affected_drugs") val affectedDrugs: List<String> = emptyList(),
    @Json(name = "clinical_recommendation") val clinicalRecommendation: String = "",
    @Json(name = "basis") val basis: String = ""
)

@JsonClass(generateAdapter = true)
data class FacialHealthScreeningResponse(
    @Json(name = "estimated_bmi_category") val estimatedBmiCategory: String = "Unknown",
    @Json(name = "bmi_confidence") val bmiConfidence: Double = 0.0,
    @Json(name = "anemia_risk_score") val anemiaRiskScore: Double = 0.0,
    @Json(name = "cardiovascular_risk_indicators") val cardiovascularRiskIndicators: List<String> = emptyList(),
    @Json(name = "thyroid_indicators") val thyroidIndicators: List<String> = emptyList(),
    @Json(name = "fatigue_stress_score") val fatigueStressScore: Double = 0.0,
    @Json(name = "hydration_score") val hydrationScore: Double = 50.0
)

@JsonClass(generateAdapter = true)
data class DermatologicalAnalysisResponse(
    @Json(name = "rosacea_risk_score") val rosaceaRiskScore: Double = 0.0,
    @Json(name = "melasma_risk_score") val melasmaRiskScore: Double = 0.0,
    @Json(name = "photo_aging_gap") val photoAgingGap: Int = 0,
    @Json(name = "acne_severity_score") val acneSeverityScore: Double = 0.0,
    @Json(name = "skin_cancer_risk_factors") val skinCancerRiskFactors: List<String> = emptyList(),
    @Json(name = "pigmentation_disorder_risk") val pigmentationDisorderRisk: Double = 0.0,
    @Json(name = "moisture_barrier_score") val moistureBarrierScore: Double = 50.0
)

@JsonClass(generateAdapter = true)
data class ConditionScreeningResponse(
    @Json(name = "condition") val condition: String = "",
    @Json(name = "risk_score") val riskScore: Double = 0.0,
    @Json(name = "facial_markers") val facialMarkers: List<String> = emptyList(),
    @Json(name = "confidence") val confidence: Double = 0.0,
    @Json(name = "recommendation") val recommendation: String = ""
)

@JsonClass(generateAdapter = true)
data class AncestryDerivedPredictionsResponse(
    @Json(name = "predicted_mtdna_haplogroup") val predictedMtdnaHaplogroup: String = "Unknown",
    @Json(name = "haplogroup_confidence") val haplogroupConfidence: Double = 0.0,
    @Json(name = "lactose_tolerance_probability") val lactoseToleranceProbability: Double = 0.5,
    @Json(name = "alcohol_flush_probability") val alcoholFlushProbability: Double = 0.0,
    @Json(name = "caffeine_sensitivity") val caffeineSensitivity: String = "Unknown",
    @Json(name = "bitter_taste_sensitivity") val bitterTasteSensitivity: String = "Unknown",
    @Json(name = "population_specific_risks") val populationSpecificRisks: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class FacialAnalysisResult(
    @Json(name = "image_type") val imageType: String = "face_photo",
    @Json(name = "estimated_biological_age") val estimatedBiologicalAge: Int = 0,
    @Json(name = "estimated_telomere_length_kb") val estimatedTelomereLengthKb: Double = 0.0,
    @Json(name = "telomere_percentile") val telomerePercentile: Int = 50,
    @Json(name = "skin_health_score") val skinHealthScore: Double = 0.0,
    @Json(name = "oxidative_stress_score") val oxidativeStressScore: Double = 0.0,
    @Json(name = "predicted_eye_colour") val predictedEyeColour: String = "unknown",
    @Json(name = "predicted_hair_colour") val predictedHairColour: String = "unknown",
    @Json(name = "predicted_skin_type") val predictedSkinType: String = "unknown",
    @Json(name = "measurements") val measurements: FacialMeasurementsResponse = FacialMeasurementsResponse(),
    @Json(name = "ancestry") val ancestry: AncestryEstimateResponse = AncestryEstimateResponse(),
    @Json(name = "predicted_variants") val predictedVariants: List<PredictedVariantResponse> = emptyList(),
    @Json(name = "reconstructed_dna") val reconstructedDna: ReconstructedDNAResponse? = null,
    @Json(name = "pharmacogenomic_predictions") val pharmacogenomicPredictions: List<PharmacogenomicPredictionResponse> = emptyList(),
    @Json(name = "health_screening") val healthScreening: FacialHealthScreeningResponse? = null,
    @Json(name = "dermatological_analysis") val dermatologicalAnalysis: DermatologicalAnalysisResponse? = null,
    @Json(name = "condition_screenings") val conditionScreenings: List<ConditionScreeningResponse> = emptyList(),
    @Json(name = "ancestry_derived") val ancestryDerived: AncestryDerivedPredictionsResponse? = null,
    @Json(name = "analysis_warnings") val analysisWarnings: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Full Analysis Response
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class AnalysisResponse(
    @Json(name = "job_id") val jobId: String,
    @Json(name = "image_type") val imageType: String = "fish_microscopy",
    @Json(name = "telomere_results") val telomereResults: TelomereResult,
    @Json(name = "disease_risks") val diseaseRisks: List<DiseaseRisk> = emptyList(),
    @Json(name = "diet_recommendations") val dietRecommendations: DietRecommendation,
    @Json(name = "facial_analysis") val facialAnalysis: FacialAnalysisResult? = null,
    @Json(name = "report_url") val reportUrl: String? = null,
    @Json(name = "csv_url") val csvUrl: String? = null,
    @Json(name = "created_at") val createdAt: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Job Status (for polling)
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class JobStatus(
    @Json(name = "job_id") val jobId: String,
    @Json(name = "status") val status: String = "pending",
    @Json(name = "progress_pct") val progressPct: Double = 0.0,
    @Json(name = "message") val message: String = "Job created",
    @Json(name = "result") val result: AnalysisResponse? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "updated_at") val updatedAt: String? = null
)

// ---------------------------------------------------------------------------
// Image Validation
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ImageValidationResponse(
    @Json(name = "valid") val valid: Boolean = true,
    @Json(name = "image_type") val imageType: String = "unknown",
    @Json(name = "width") val width: Int = 0,
    @Json(name = "height") val height: Int = 0,
    @Json(name = "channels") val channels: Int = 0,
    @Json(name = "file_size_bytes") val fileSizeBytes: Int = 0,
    @Json(name = "format_detected") val formatDetected: String = "unknown",
    @Json(name = "face_detected") val faceDetected: Boolean = false,
    @Json(name = "issues") val issues: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Health Check
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class HealthResponse(
    @Json(name = "status") val status: String = "ok",
    @Json(name = "version") val version: String = "",
    @Json(name = "timestamp") val timestamp: String = ""
)

// ---------------------------------------------------------------------------
// Profile-Only Analysis
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ProfileAnalysisRequest(
    @Json(name = "age") val age: Int,
    @Json(name = "sex") val sex: String,
    @Json(name = "region") val region: String,
    @Json(name = "dietary_restrictions") val dietaryRestrictions: List<String> = emptyList(),
    @Json(name = "known_variants") val knownVariants: List<String> = emptyList(),
    @Json(name = "telomere_length_kb") val telomereLengthKb: Double? = null,
    @Json(name = "include_nutrition") val includeNutrition: Boolean = true,
    @Json(name = "include_disease_risk") val includeDiseaseRisk: Boolean = true
)

@JsonClass(generateAdapter = true)
data class ProfileAnalysisResponse(
    @Json(name = "disease_risks") val diseaseRisks: List<DiseaseRisk> = emptyList(),
    @Json(name = "diet_recommendations") val dietRecommendations: DietRecommendation? = null,
    @Json(name = "overall_risk_score") val overallRiskScore: Double = 0.0,
    @Json(name = "assessed_at") val assessedAt: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Disease Risk (standalone)
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class DiseaseRiskRequest(
    @Json(name = "known_variants") val knownVariants: List<String> = emptyList(),
    @Json(name = "telomere_length") val telomereLength: Double? = null,
    @Json(name = "age") val age: Int,
    @Json(name = "sex") val sex: String,
    @Json(name = "region") val region: String
)

@JsonClass(generateAdapter = true)
data class DiseaseRiskResponse(
    @Json(name = "risks") val risks: List<DiseaseRisk> = emptyList(),
    @Json(name = "overall_risk_score") val overallRiskScore: Double = 0.0,
    @Json(name = "assessed_at") val assessedAt: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Nutrition (standalone)
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class NutritionRequest(
    @Json(name = "age") val age: Int,
    @Json(name = "sex") val sex: String,
    @Json(name = "region") val region: String,
    @Json(name = "dietary_restrictions") val dietaryRestrictions: List<String> = emptyList(),
    @Json(name = "known_variants") val knownVariants: List<String> = emptyList(),
    @Json(name = "health_conditions") val healthConditions: List<String> = emptyList(),
    @Json(name = "calorie_target") val calorieTarget: Int = 2000,
    @Json(name = "meal_plan_days") val mealPlanDays: Int = 7
)

@JsonClass(generateAdapter = true)
data class NutritionResponse(
    @Json(name = "recommendation") val recommendation: DietRecommendation,
    @Json(name = "generated_at") val generatedAt: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Health Checkup – Report Parse Preview
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ReportParsePreview(
    @Json(name = "extracted_blood_tests") val extractedBloodTests: Map<String, Double> = emptyMap(),
    @Json(name = "extracted_urine_tests") val extractedUrineTests: Map<String, Double> = emptyMap(),
    @Json(name = "extracted_abdomen_notes") val extractedAbdomenNotes: String = "",
    @Json(name = "unrecognized_lines") val unrecognizedLines: List<String> = emptyList(),
    @Json(name = "confidence") val confidence: Double = 0.0,
    @Json(name = "file_type") val fileType: String = "",
    @Json(name = "text_length") val textLength: Int = 0
)

// ---------------------------------------------------------------------------
// Health Checkup – Lab Result
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class LabResultItem(
    @Json(name = "parameter") val parameter: String = "",
    @Json(name = "display_name") val displayName: String = "",
    @Json(name = "value") val value: Double = 0.0,
    @Json(name = "unit") val unit: String = "",
    @Json(name = "status") val status: String = "normal",
    @Json(name = "reference_low") val referenceLow: Double = 0.0,
    @Json(name = "reference_high") val referenceHigh: Double = 0.0,
    @Json(name = "category") val category: String = ""
)

// ---------------------------------------------------------------------------
// Health Checkup – Health Finding
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class HealthFindingItem(
    @Json(name = "condition") val condition: String = "",
    @Json(name = "display_name") val displayName: String = "",
    @Json(name = "severity") val severity: String = "mild",
    @Json(name = "evidence") val evidence: List<String> = emptyList(),
    @Json(name = "dietary_impact") val dietaryImpact: String = "",
    @Json(name = "nutrients_to_increase") val nutrientsToIncrease: List<String> = emptyList(),
    @Json(name = "nutrients_to_decrease") val nutrientsToDecrease: List<String> = emptyList(),
    @Json(name = "foods_to_increase") val foodsToIncrease: List<String> = emptyList(),
    @Json(name = "foods_to_avoid") val foodsToAvoid: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Health Checkup – Score Breakdown
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class HealthScoreBreakdown(
    @Json(name = "CBC") val cbc: Double? = null,
    @Json(name = "Lipid Panel") val lipidPanel: Double? = null,
    @Json(name = "Liver Function") val liverFunction: Double? = null,
    @Json(name = "Kidney Function") val kidneyFunction: Double? = null,
    @Json(name = "Diabetes Panel") val diabetesPanel: Double? = null,
    @Json(name = "Thyroid Panel") val thyroidPanel: Double? = null,
    @Json(name = "Vitamins & Minerals") val vitamins: Double? = null,
    @Json(name = "Electrolytes") val electrolytes: Double? = null,
    @Json(name = "Inflammation") val inflammation: Double? = null,
    @Json(name = "Urine Analysis") val urineAnalysis: Double? = null,
    @Json(name = "Abdomen Scan") val abdomenScan: Double? = null
)

// ---------------------------------------------------------------------------
// Health Checkup – Abdomen Finding
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class AbdomenFindingItem(
    @Json(name = "organ") val organ: String = "",
    @Json(name = "finding") val finding: String = "",
    @Json(name = "severity") val severity: String = "mild",
    @Json(name = "dietary_impact") val dietaryImpact: String = "",
    @Json(name = "foods_to_avoid") val foodsToAvoid: List<String> = emptyList(),
    @Json(name = "foods_to_increase") val foodsToIncrease: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Health Checkup – Ayurvedic Remedy
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class AyurvedicRemedyItem(
    @Json(name = "name") val name: String = "",
    @Json(name = "ingredients") val ingredients: List<String> = emptyList(),
    @Json(name = "preparation") val preparation: String = "",
    @Json(name = "dosage") val dosage: String = "",
    @Json(name = "source") val source: String = "",
    @Json(name = "mechanism") val mechanism: String = "",
    @Json(name = "for_conditions") val forConditions: List<String> = emptyList()
)

// ---------------------------------------------------------------------------
// Health Checkup – Ayurvedic Analysis
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class AyurvedicAnalysis(
    @Json(name = "dosha_assessment") val doshaAssessment: String = "",
    @Json(name = "remedies") val remedies: List<AyurvedicRemedyItem> = emptyList(),
    @Json(name = "lifestyle_recommendations") val lifestyleRecommendations: List<String> = emptyList(),
    @Json(name = "yoga_asanas") val yogaAsanas: List<String> = emptyList(),
    @Json(name = "pranayama") val pranayama: List<String> = emptyList(),
    @Json(name = "dietary_principles") val dietaryPrinciples: List<String> = emptyList(),
    @Json(name = "contraindications") val contraindications: List<String> = emptyList(),
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Health Checkup – Upload Response
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class HealthCheckupResponse(
    @Json(name = "lab_results") val labResults: List<LabResultItem> = emptyList(),
    @Json(name = "abnormal_count") val abnormalCount: Int = 0,
    @Json(name = "total_tested") val totalTested: Int = 0,
    @Json(name = "findings") val findings: List<HealthFindingItem> = emptyList(),
    @Json(name = "abdomen_findings") val abdomenFindings: List<AbdomenFindingItem> = emptyList(),
    @Json(name = "detected_conditions") val detectedConditions: List<String> = emptyList(),
    @Json(name = "overall_health_score") val overallHealthScore: Double = 0.0,
    @Json(name = "health_score_breakdown") val healthScoreBreakdown: Map<String, Double> = emptyMap(),
    @Json(name = "diet_recommendation") val dietRecommendation: DietRecommendation? = null,
    @Json(name = "dietary_modifications") val dietaryModifications: List<String> = emptyList(),
    @Json(name = "calorie_adjustment") val calorieAdjustment: Int = 0,
    @Json(name = "ayurvedic_analysis") val ayurvedicAnalysis: AyurvedicAnalysis? = null,
    @Json(name = "llm_analysis") val llmAnalysis: String? = null,
    @Json(name = "analyzed_at") val analyzedAt: String = "",
    @Json(name = "disclaimer") val disclaimer: String = ""
)

// ---------------------------------------------------------------------------
// Psychiatry / Counselling
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class CounselRequest(
    @Json(name = "message") val message: String,
    @Json(name = "conversation") val conversation: List<CounselMessage> = emptyList(),
    @Json(name = "history") val history: List<Map<String, Any>> = emptyList()
)

@JsonClass(generateAdapter = true)
data class CounselMessage(
    @Json(name = "role") val role: String,
    @Json(name = "text") val text: String
)

@JsonClass(generateAdapter = true)
data class CounselResponse(
    @Json(name = "theme") val theme: String = "",
    @Json(name = "theme_title") val themeTitle: String = "",
    @Json(name = "ai_response") val aiResponse: String? = null,
    @Json(name = "response") val response: String? = null,
    @Json(name = "inquiry") val inquiry: String? = null,
    @Json(name = "insight") val insight: String? = null,
    @Json(name = "source_quote") val sourceQuote: String? = null,
    @Json(name = "source_author") val sourceAuthor: String? = null,
    @Json(name = "mode") val mode: String = "template",
    @Json(name = "followups") val followups: List<String> = emptyList()
) {
    /** Get the best available response text */
    val displayText: String
        get() = aiResponse
            ?: response
            ?: listOfNotNull(inquiry, insight).joinToString("\n\n").ifEmpty { "I hear you. Let's explore that together." }
}

@JsonClass(generateAdapter = true)
data class ThemesResponse(
    @Json(name = "themes") val themes: Map<String, ThemeInfo> = emptyMap(),
    @Json(name = "count") val count: Int = 0
)

@JsonClass(generateAdapter = true)
data class ThemeInfo(
    @Json(name = "title") val title: String = "",
    @Json(name = "description") val description: String = "",
    @Json(name = "core_insights") val coreInsights: List<String> = emptyList(),
    @Json(name = "quote_count") val quoteCount: Int = 0,
    @Json(name = "inquiry_count") val inquiryCount: Int = 0
)

// ---------------------------------------------------------------------------
// Consent Token (server-side DPDP compliance)
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ConsentTokenRequest(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "data_principal_age_confirmed") val agConfirmed: Boolean = true,
    @Json(name = "consents") val consents: List<ConsentPurpose>
)

@JsonClass(generateAdapter = true)
data class ConsentPurpose(
    @Json(name = "purpose") val purpose: String,
    @Json(name = "granted") val granted: Boolean = true
)

@JsonClass(generateAdapter = true)
data class ConsentTokenResponse(
    @Json(name = "status") val status: String = "",
    @Json(name = "consent_token") val consentToken: String = "",
    @Json(name = "session_id") val sessionId: String = "",
    @Json(name = "granted_purposes") val grantedPurposes: List<String> = emptyList()
)
