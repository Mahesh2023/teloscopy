package com.teloscopy.app.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.Biotech
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Face
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.teloscopy.app.data.api.AnalysisResponse
import com.teloscopy.app.data.api.DietRecommendation
import com.teloscopy.app.data.api.FacialAnalysisResult
import com.teloscopy.app.data.api.TelomereResult
import com.teloscopy.app.ui.components.DiseaseRiskCard
import com.teloscopy.app.ui.components.MealPlanCard
import com.teloscopy.app.ui.theme.Primary
import com.teloscopy.app.ui.theme.RiskHigh
import com.teloscopy.app.ui.theme.RiskLow
import com.teloscopy.app.ui.theme.SurfaceVariant
import com.teloscopy.app.ui.theme.Tertiary
import com.teloscopy.app.viewmodel.AnalysisViewModel

// ─────────────────────────────────────────────────────────────────────────────
// ResultsScreen – top-level composable
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Displays the full analysis results after the pipeline completes.
 *
 * @param jobId     The analysis job identifier used to fetch results.
 * @param viewModel Shared [AnalysisViewModel] (Hilt-provided).
 * @param onBack    Callback invoked when the user presses the back arrow.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(
    jobId: String,
    viewModel: AnalysisViewModel = hiltViewModel(),
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // Fetch results if they are not already present (e.g. direct navigation).
    LaunchedEffect(jobId) {
        if (uiState.result == null && !uiState.isLoading) {
            viewModel.loadResults(jobId)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Analysis Results",
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                    navigationIconContentColor = MaterialTheme.colorScheme.primary
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                // Loading – no result yet and no error
                uiState.isLoading && uiState.result == null -> {
                    LoadingContent()
                }
                // Error – no result available
                uiState.error != null && uiState.result == null -> {
                    ErrorContent(
                        error = uiState.error!!,
                        onRetry = { viewModel.loadResults(jobId) }
                    )
                }
                // Result available
                uiState.result != null -> {
                    ResultsContent(result = uiState.result!!)
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading state
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun LoadingContent() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(
                color = MaterialTheme.colorScheme.primary,
                strokeWidth = 3.dp
            )
            Spacer(Modifier.height(16.dp))
            Text(
                text = "Loading results\u2026",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Error state
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun ErrorContent(error: String, onRetry: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        ElevatedCard(
            colors = CardDefaults.elevatedCardColors(
                containerColor = MaterialTheme.colorScheme.errorContainer
            )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    imageVector = Icons.Outlined.ErrorOutline,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    text = "Something went wrong",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = error,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(20.dp))
                Button(onClick = onRetry) {
                    Text("Retry")
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main results content (LazyColumn)
// ─────────────────────────────────────────────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ResultsContent(result: AnalysisResponse) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // ── (a) Summary card ─────────────────────────────────────────────
        item(key = "summary") {
            SummaryCard(result)
        }

        // ── (b) Telomere results (always present – non-nullable) ─────────
        item(key = "telomere_header") {
            SectionHeader(
                icon = Icons.Outlined.Biotech,
                title = "Telomere Results"
            )
        }
        item(key = "telomere_content") {
            TelomereResultsSection(telomere = result.telomereResults)
        }

        // ── (c) Facial analysis (nullable) ───────────────────────────────
        if (result.facialAnalysis != null) {
            item(key = "facial_header") {
                SectionHeader(
                    icon = Icons.Outlined.Face,
                    title = "Facial Analysis"
                )
            }
            item(key = "facial_content") {
                FacialAnalysisSection(facial = result.facialAnalysis!!)
            }
        }

        // ── (d) Disease risks ────────────────────────────────────────────
        if (result.diseaseRisks.isNotEmpty()) {
            item(key = "disease_header") {
                SectionHeader(
                    icon = Icons.Outlined.Warning,
                    title = "Disease Risks"
                )
            }
            items(
                items = result.diseaseRisks,
                key = { it.disease }
            ) { risk ->
                DiseaseRiskCard(risk = risk)
            }
        }

        // ── (e) Diet recommendations (always present – non-nullable) ─────
        item(key = "diet_header") {
            SectionHeader(
                icon = Icons.Outlined.Restaurant,
                title = "Diet Recommendations"
            )
        }
        item(key = "diet_content") {
            DietRecommendationsSection(diet = result.dietRecommendations)
        }

        // ── (f) Disclaimer ───────────────────────────────────────────────
        item(key = "disclaimer") {
            DisclaimerSection(text = result.disclaimer)
        }

        // Bottom spacer for safe-area / nav-bar clearance
        item(key = "bottom_spacer") {
            Spacer(Modifier.height(32.dp))
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Section header
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun SectionHeader(icon: ImageVector, title: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(top = 8.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(24.dp)
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onBackground
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// (a) Summary card
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun SummaryCard(result: AnalysisResponse) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Image type badge
                val isFacePhoto = result.imageType.lowercase() == "face_photo"
                val badgeColor = if (isFacePhoto) {
                    MaterialTheme.colorScheme.secondary
                } else {
                    MaterialTheme.colorScheme.primary
                }
                val badgeLabel = if (isFacePhoto) "Face Photo" else "FISH Microscopy"

                Surface(
                    color = badgeColor.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = badgeLabel,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                        color = badgeColor,
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.Bold
                        )
                    )
                }

                // Created-at timestamp
                Text(
                    text = formatTimestamp(result.createdAt),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(Modifier.height(10.dp))

            // Job ID in small muted text
            Text(
                text = "Job ID: ${result.jobId}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// (b) Telomere results section
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun TelomereResultsSection(telomere: TelomereResult) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // Biological Age – large prominent display
        ElevatedCard(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Biological Age Estimate",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = "${telomere.biologicalAgeEstimate}",
                    style = MaterialTheme.typography.displayLarge.copy(
                        fontSize = 56.sp,
                        fontWeight = FontWeight.Bold
                    ),
                    color = Tertiary
                )
                Text(
                    text = "years",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Three stat cards in a row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            StatCard(
                value = String.format("%.2f", telomere.meanLength),
                label = "Mean Length\n(kb)",
                modifier = Modifier.weight(1f)
            )
            StatCard(
                value = String.format("%.2f", telomere.stdDev),
                label = "Std Dev",
                modifier = Modifier.weight(1f)
            )
            StatCard(
                value = String.format("%.2f", telomere.tsRatio),
                label = "T/S Ratio",
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun StatCard(
    value: String,
    label: String,
    modifier: Modifier = Modifier
) {
    ElevatedCard(
        modifier = modifier,
        colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                color = Primary
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// (c) Facial analysis section
// ─────────────────────────────────────────────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun FacialAnalysisSection(facial: FacialAnalysisResult) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // Grid of info chips
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            InfoChip(
                label = "Bio Age",
                value = "${facial.estimatedBiologicalAge}"
            )
            InfoChip(
                label = "Telomere",
                value = String.format("%.2f kb", facial.estimatedTelomereLengthKb)
            )
            InfoChip(
                label = "Percentile",
                value = "${facial.telomerePercentile}th"
            )
            InfoChip(
                label = "Skin Health",
                value = String.format("%.1f", facial.skinHealthScore)
            )
            InfoChip(
                label = "Oxidative Stress",
                value = String.format("%.1f", facial.oxidativeStressScore)
            )
        }

        HorizontalDivider(
            color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
            modifier = Modifier.padding(vertical = 4.dp)
        )

        // Predicted traits row
        Text(
            text = "Predicted Traits",
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            TraitBadge(text = "Eye: ${facial.predictedEyeColour}")
            TraitBadge(text = "Hair: ${facial.predictedHairColour}")
            TraitBadge(text = "Skin: ${facial.predictedSkinType}")
        }
    }
}

@Composable
private fun InfoChip(label: String, value: String) {
    Surface(
        color = SurfaceVariant,
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                style = MaterialTheme.typography.titleLarge.copy(
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                ),
                color = Primary
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun TraitBadge(text: String) {
    Surface(
        color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.12f),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Medium),
            color = MaterialTheme.colorScheme.secondary
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// (e) Diet recommendations section
// ─────────────────────────────────────────────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DietRecommendationsSection(diet: DietRecommendation) {
    Column(
        modifier = Modifier.animateContentSize(),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Summary text
        Text(
            text = diet.summary,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onBackground
        )

        // Key Nutrients as chips
        if (diet.keyNutrients.isNotEmpty()) {
            Text(
                text = "Key Nutrients",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                diet.keyNutrients.forEach { nutrient ->
                    NutrientChip(text = nutrient)
                }
            }
        }

        // Foods to Increase (green-tinted)
        if (diet.foodsToIncrease.isNotEmpty()) {
            FoodList(
                title = "Foods to Increase",
                items = diet.foodsToIncrease,
                tintColor = RiskLow
            )
        }

        // Foods to Avoid (red-tinted)
        if (diet.foodsToAvoid.isNotEmpty()) {
            FoodList(
                title = "Foods to Avoid",
                items = diet.foodsToAvoid,
                tintColor = RiskHigh
            )
        }

        // Calorie target
        if (diet.calorieTarget != null) {
            ElevatedCard(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Daily Calorie Target",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = "${diet.calorieTarget} kcal",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                        color = Primary
                    )
                }
            }
        }

        // Meal plans
        if (diet.mealPlans.isNotEmpty()) {
            HorizontalDivider(
                color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                modifier = Modifier.padding(vertical = 4.dp)
            )
            Text(
                text = "Meal Plans",
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onBackground
            )
            diet.mealPlans.forEach { plan ->
                MealPlanCard(mealPlan = plan)
            }
        }
    }
}

@Composable
private fun NutrientChip(text: String) {
    Surface(
        color = Tertiary.copy(alpha = 0.12f),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Medium),
            color = Tertiary
        )
    }
}

@Composable
private fun FoodList(
    title: String,
    items: List<String>,
    tintColor: Color
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = tintColor.copy(alpha = 0.06f)
        )
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = tintColor
            )
            Spacer(Modifier.height(8.dp))
            items.forEach { item ->
                Row(
                    modifier = Modifier.padding(vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(6.dp)
                            .background(
                                color = tintColor.copy(alpha = 0.7f),
                                shape = RoundedCornerShape(3.dp)
                            )
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = item,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// (f) Disclaimer
// ─────────────────────────────────────────────────────────────────────────────

@Composable
private fun DisclaimerSection(text: String) {
    Column(modifier = Modifier.padding(top = 8.dp)) {
        HorizontalDivider(
            color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium.copy(
                fontSize = 11.sp,
                lineHeight = 16.sp
            ),
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Best-effort formatting of an ISO-8601 timestamp string into a more
 * readable date. Falls back to the raw string if parsing fails.
 */
private fun formatTimestamp(raw: String): String {
    return try {
        // Handle "2024-03-15T10:30:00Z" or similar ISO format
        val dateTimePart = raw.substringBefore("T")
        val parts = dateTimePart.split("-")
        if (parts.size == 3) {
            val months = arrayOf(
                "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            )
            val month = parts[1].toIntOrNull() ?: return raw
            val day = parts[2].toIntOrNull() ?: return raw
            val year = parts[0]
            "${months.getOrElse(month) { "???" }} $day, $year"
        } else {
            raw
        }
    } catch (_: Exception) {
        raw
    }
}
