package com.teloscopy.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Healing
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.Science
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.Analytics
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.Science
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.foundation.BorderStroke
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.teloscopy.app.data.api.DietRecommendation
import com.teloscopy.app.data.api.HealthCheckupResponse
import com.teloscopy.app.data.api.HealthFindingItem
import com.teloscopy.app.data.api.LabResultItem
import com.teloscopy.app.data.api.MealPlan
import com.teloscopy.app.data.api.ReportParsePreview
import com.teloscopy.app.ui.components.MealPlanCard
import com.teloscopy.app.ui.theme.Primary
import com.teloscopy.app.ui.theme.RiskHigh
import com.teloscopy.app.ui.theme.RiskLow
import com.teloscopy.app.ui.theme.RiskModerate
import com.teloscopy.app.ui.theme.Secondary
import com.teloscopy.app.ui.theme.SurfaceVariant
import com.teloscopy.app.ui.theme.Tertiary
import com.teloscopy.app.ui.theme.WarningAmber
import com.teloscopy.app.viewmodel.CheckupState
import com.teloscopy.app.viewmodel.HealthCheckupViewModel

// ── Region options for Health Checkup ────────────────────────────────────────
private val healthCheckupRegions = listOf(
    "South Indian",
    "North Indian",
    "East Indian",
    "West Indian",
    "Mediterranean",
    "East Asian",
    "Western"
)

// ── Sex options ──────────────────────────────────────────────────────────────
private val sexOptions = listOf("male", "female")

// ═════════════════════════════════════════════════════════════════════════════
// HealthCheckupScreen
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Comprehensive health checkup screen supporting lab report upload,
 * value extraction preview, and full analysis results display.
 *
 * The flow is:
 * 1. User uploads a lab report (PDF / image / text).
 * 2. Optionally extracts values first for preview, or goes straight to analysis.
 * 3. Results display health score, lab results table, findings, diet, etc.
 *
 * @param viewModel The [HealthCheckupViewModel] managing state and API calls.
 * @param onBack    Callback invoked when the user presses the back arrow.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun HealthCheckupScreen(
    viewModel: HealthCheckupViewModel,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }

    // ── ViewModel state observation ──────────────────────────────────────
    val state by viewModel.state.collectAsStateWithLifecycle()
    val parsePreview by viewModel.parsePreview.collectAsStateWithLifecycle()
    val checkupResponse by viewModel.checkupResponse.collectAsStateWithLifecycle()
    val errorMessage by viewModel.errorMessage.collectAsStateWithLifecycle()
    val selectedFileUri by viewModel.selectedFileUri.collectAsStateWithLifecycle()
    val selectedFileName by viewModel.selectedFileName.collectAsStateWithLifecycle()

    // ── Local form state ─────────────────────────────────────────────────
    var age by remember { mutableStateOf(viewModel.age) }
    var selectedSex by remember { mutableStateOf(viewModel.sex) }
    var selectedRegion by remember { mutableStateOf(viewModel.region) }
    var profileExpanded by remember { mutableStateOf(false) }
    var sexDropdownExpanded by remember { mutableStateOf(false) }
    var regionDropdownExpanded by remember { mutableStateOf(false) }

    // ── File picker launcher ─────────────────────────────────────────────
    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let {
            // Persist read permission for the URI
            context.contentResolver.takePersistableUriPermission(
                it,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
            val cursor = context.contentResolver.query(it, null, null, null, null)
            val displayName = cursor?.use { c ->
                val nameIndex = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (c.moveToFirst() && nameIndex >= 0) c.getString(nameIndex) else "unknown"
            } ?: "unknown"
            viewModel.setFile(it, displayName)
        }
    }

    // ── Helper: read bytes from the selected URI ─────────────────────────
    fun readFileBytes(): ByteArray? {
        val uri = selectedFileUri ?: return null
        return try {
            context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
        } catch (e: Exception) {
            null
        }
    }

    // ── Sync local form state to ViewModel ───────────────────────────────
    LaunchedEffect(age) { viewModel.age = age }
    LaunchedEffect(selectedSex) { viewModel.sex = selectedSex }
    LaunchedEffect(selectedRegion) { viewModel.region = selectedRegion }

    // ── Show Snackbar on error ───────────────────────────────────────────
    LaunchedEffect(errorMessage) {
        val msg = errorMessage
        if (msg != null) {
            val result = snackbarHostState.showSnackbar(
                message = msg,
                actionLabel = "Dismiss",
                duration = SnackbarDuration.Long
            )
            if (result == SnackbarResult.ActionPerformed ||
                result == SnackbarResult.Dismissed
            ) {
                viewModel.dismissError()
            }
        }
    }

    // ── Form validation ──────────────────────────────────────────────────
    val ageValue = age.toIntOrNull()
    val isAgeValid = ageValue != null && ageValue in 1..120
    val hasFile = selectedFileUri != null
    val canExtract = hasFile
    val canAnalyze = hasFile && age.isNotBlank() && isAgeValid &&
            selectedSex.isNotBlank() && selectedRegion.isNotBlank()

    // ═════════════════════════════════════════════════════════════════════
    // UI
    // ═════════════════════════════════════════════════════════════════════

    Scaffold(
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState) { data ->
                Snackbar(
                    snackbarData = data,
                    containerColor = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        },
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Health Checkup",
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ─────────────────────────────────────────────────────────────
            // Section 1: File Upload
            // ─────────────────────────────────────────────────────────────
            item(key = "upload_header") {
                Spacer(modifier = Modifier.height(4.dp))
            }

            item(key = "upload_card") {
                FileUploadCard(
                    selectedFileName = if (hasFile) selectedFileName else null,
                    selectedFileUri = selectedFileUri,
                    onPickFile = {
                        filePickerLauncher.launch(
                            arrayOf(
                                "application/pdf",
                                "image/png",
                                "image/jpeg",
                                "text/plain"
                            )
                        )
                    },
                    onClear = { viewModel.clearFile() },
                    onExtract = {
                        val bytes = readFileBytes()
                        if (bytes != null) {
                            viewModel.parseReport(bytes, selectedFileName)
                        }
                    },
                    onUploadAndAnalyze = {
                        val bytes = readFileBytes()
                        if (bytes != null) {
                            viewModel.uploadAndAnalyze(bytes, selectedFileName)
                        }
                    },
                    canExtract = canExtract,
                    canAnalyze = canAnalyze,
                    isLoading = state == CheckupState.PARSING || state == CheckupState.ANALYZING
                )
            }

            // ─────────────────────────────────────────────────────────────
            // Section 2: Profile Information (collapsible)
            // ─────────────────────────────────────────────────────────────
            item(key = "profile_card") {
                ProfileCard(
                    expanded = profileExpanded,
                    onToggleExpanded = { profileExpanded = !profileExpanded },
                    age = age,
                    onAgeChange = { newValue ->
                        if (newValue.length <= 3 && newValue.all { it.isDigit() }) {
                            age = newValue
                        }
                    },
                    isAgeValid = age.isBlank() || isAgeValid,
                    selectedSex = selectedSex,
                    onSexChange = { selectedSex = it },
                    sexDropdownExpanded = sexDropdownExpanded,
                    onSexDropdownExpandedChange = { sexDropdownExpanded = it },
                    selectedRegion = selectedRegion,
                    onRegionChange = { selectedRegion = it },
                    regionDropdownExpanded = regionDropdownExpanded,
                    onRegionDropdownExpandedChange = { regionDropdownExpanded = it }
                )
            }

            // ─────────────────────────────────────────────────────────────
            // Loading States
            // ─────────────────────────────────────────────────────────────
            if (state == CheckupState.PARSING) {
                item(key = "parsing_loader") {
                    LoadingIndicator(message = "Extracting lab values\u2026")
                }
            }

            if (state == CheckupState.ANALYZING) {
                item(key = "analyzing_loader") {
                    LoadingIndicator(message = "Analysing your health report\u2026")
                }
            }

            // ─────────────────────────────────────────────────────────────
            // Section 3: Extraction Preview (shown when PARSED)
            // ─────────────────────────────────────────────────────────────
            if (state == CheckupState.PARSED && parsePreview != null) {
                item(key = "preview_section") {
                    ExtractionPreviewSection(
                        preview = parsePreview!!,
                        onProceedToAnalyze = {
                            val bytes = readFileBytes()
                            if (bytes != null) {
                                viewModel.uploadAndAnalyze(bytes, selectedFileName)
                            }
                        },
                        canAnalyze = canAnalyze
                    )
                }
            }

            // ─────────────────────────────────────────────────────────────
            // Section 4: Error State with Retry
            // ─────────────────────────────────────────────────────────────
            if (state == CheckupState.ERROR && errorMessage != null) {
                item(key = "error_section") {
                    ErrorCard(
                        errorMessage = errorMessage!!,
                        onRetry = { viewModel.reset() },
                        onDismiss = { viewModel.dismissError() }
                    )
                }
            }

            // ─────────────────────────────────────────────────────────────
            // Section 5: Full Results (shown when RESULTS)
            // ─────────────────────────────────────────────────────────────
            if (state == CheckupState.RESULTS && checkupResponse != null) {
                val response = checkupResponse!!

                // (a) Health Score Card
                item(key = "health_score") {
                    HealthScoreCard(
                        score = response.overallHealthScore,
                        breakdown = response.healthScoreBreakdown,
                        totalTested = response.totalTested,
                        abnormalCount = response.abnormalCount
                    )
                }

                // (b) Lab Results Table
                if (response.labResults.isNotEmpty()) {
                    item(key = "lab_results_header") {
                        CheckupSectionHeader(
                            icon = Icons.Outlined.Science,
                            title = "Lab Results"
                        )
                    }
                    item(key = "lab_results_table") {
                        LabResultsTableCard(labResults = response.labResults)
                    }
                }

                // (c) Health Findings
                if (response.findings.isNotEmpty()) {
                    item(key = "findings_header") {
                        CheckupSectionHeader(
                            icon = Icons.Filled.Healing,
                            title = "Health Findings"
                        )
                    }
                    items(
                        items = response.findings,
                        key = { it.condition }
                    ) { finding ->
                        HealthFindingCard(finding = finding)
                    }
                }

                // (d) Detected Conditions Chips
                if (response.detectedConditions.isNotEmpty()) {
                    item(key = "conditions_header") {
                        CheckupSectionHeader(
                            icon = Icons.Filled.Info,
                            title = "Detected Conditions"
                        )
                    }
                    item(key = "conditions_chips") {
                        DetectedConditionsChips(
                            conditions = response.detectedConditions
                        )
                    }
                }

                // (e) Diet Recommendation
                if (response.dietRecommendation != null) {
                    item(key = "diet_header") {
                        CheckupSectionHeader(
                            icon = Icons.Outlined.Restaurant,
                            title = "Diet Recommendations"
                        )
                    }
                    item(key = "diet_content") {
                        DietRecommendationCard(
                            diet = response.dietRecommendation!!
                        )
                    }
                }

                // (f) Ayurvedic Remedies Section
                item(key = "ayurvedic_section") {
                    response.ayurvedicAnalysis?.let { ayurvedic ->
                        if (ayurvedic.remedies.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(16.dp))
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF7ED)),
                                border = BorderStroke(1.dp, Color(0xFFD97706))
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text(
                                        "Ayurvedic Home Remedies",
                                        style = MaterialTheme.typography.titleMedium,
                                        color = Color(0xFFD97706),
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        "Based on Charaka Samhita & Sushruta Samhita",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color.Gray
                                    )
                                    Spacer(modifier = Modifier.height(12.dp))

                                    // Dosha Assessment
                                    if (ayurvedic.doshaAssessment.isNotEmpty()) {
                                        Surface(
                                            modifier = Modifier.fillMaxWidth(),
                                            color = Color(0xFFFEF3C7),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Column(modifier = Modifier.padding(12.dp)) {
                                                Text("Dosha Assessment", fontWeight = FontWeight.SemiBold, fontSize = 14.sp, color = Color(0xFFD97706))
                                                Text(ayurvedic.doshaAssessment, fontSize = 13.sp, color = Color(0xFF78350F))
                                            }
                                        }
                                        Spacer(modifier = Modifier.height(12.dp))
                                    }

                                    // Remedies
                                    Text("Recommended Remedies", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                                    Spacer(modifier = Modifier.height(8.dp))
                                    ayurvedic.remedies.forEachIndexed { idx, remedy ->
                                        Surface(
                                            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                                            color = Color(0xFFFFFBEB),
                                            shape = RoundedCornerShape(8.dp),
                                            border = BorderStroke(1.dp, Color(0xFFD97706).copy(alpha = 0.19f))
                                        ) {
                                            Column(modifier = Modifier.padding(12.dp)) {
                                                Row(
                                                    modifier = Modifier.fillMaxWidth(),
                                                    horizontalArrangement = Arrangement.SpaceBetween,
                                                    verticalAlignment = Alignment.Top
                                                ) {
                                                    Text(
                                                        "${idx + 1}. ${remedy.name}",
                                                        fontWeight = FontWeight.SemiBold,
                                                        fontSize = 14.sp,
                                                        modifier = Modifier.weight(1f)
                                                    )
                                                    Surface(
                                                        color = Color(0xFFFDE68A),
                                                        shape = RoundedCornerShape(12.dp)
                                                    ) {
                                                        Text(
                                                            remedy.source,
                                                            fontSize = 10.sp,
                                                            color = Color(0xFFD97706),
                                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                        )
                                                    }
                                                }
                                                if (remedy.ingredients.isNotEmpty()) {
                                                    Text("Ingredients: ${remedy.ingredients.joinToString(", ")}", fontSize = 12.sp, color = Color.DarkGray)
                                                }
                                                if (remedy.preparation.isNotEmpty()) {
                                                    Text("Preparation: ${remedy.preparation}", fontSize = 12.sp, color = Color.DarkGray)
                                                }
                                                if (remedy.dosage.isNotEmpty()) {
                                                    Text("Dosage: ${remedy.dosage}", fontSize = 12.sp, color = Color.DarkGray)
                                                }
                                                if (remedy.mechanism.isNotEmpty()) {
                                                    Text(remedy.mechanism, fontSize = 12.sp, color = Color.Gray, fontStyle = FontStyle.Italic)
                                                }
                                                if (remedy.forConditions.isNotEmpty()) {
                                                    Spacer(modifier = Modifier.height(4.dp))
                                                    FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                                        remedy.forConditions.forEach { cond ->
                                                            Surface(color = Color(0xFFFDE68A), shape = RoundedCornerShape(10.dp)) {
                                                                Text(
                                                                    cond.replace("_", " "),
                                                                    fontSize = 10.sp,
                                                                    color = Color(0xFFB45309),
                                                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                                )
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Yoga & Pranayama
                                    if (ayurvedic.yogaAsanas.isNotEmpty() || ayurvedic.pranayama.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Row(modifier = Modifier.fillMaxWidth()) {
                                            if (ayurvedic.yogaAsanas.isNotEmpty()) {
                                                Column(modifier = Modifier.weight(1f)) {
                                                    Text("Yoga Asanas", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                                                    ayurvedic.yogaAsanas.forEach { asana ->
                                                        Text("• $asana", fontSize = 12.sp, color = Color.DarkGray)
                                                    }
                                                }
                                            }
                                            if (ayurvedic.pranayama.isNotEmpty()) {
                                                Column(modifier = Modifier.weight(1f)) {
                                                    Text("Pranayama", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                                                    ayurvedic.pranayama.forEach { p ->
                                                        Text("• $p", fontSize = 12.sp, color = Color.DarkGray)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Lifestyle
                                    if (ayurvedic.lifestyleRecommendations.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Text("Lifestyle (Dinacharya)", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                                        ayurvedic.lifestyleRecommendations.forEach { l ->
                                            Text("• $l", fontSize = 12.sp, color = Color.DarkGray)
                                        }
                                    }

                                    // Dietary Principles
                                    if (ayurvedic.dietaryPrinciples.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Text("Dietary Principles (Pathya-Apathya)", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                                        ayurvedic.dietaryPrinciples.forEach { d ->
                                            Text("• $d", fontSize = 12.sp, color = Color.DarkGray)
                                        }
                                    }

                                    // Contraindications
                                    if (ayurvedic.contraindications.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Surface(
                                            modifier = Modifier.fillMaxWidth(),
                                            color = Color(0xFFFEE2E2),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Column(modifier = Modifier.padding(12.dp)) {
                                                Text("Contraindications", fontWeight = FontWeight.SemiBold, fontSize = 13.sp, color = Color(0xFFEF4444))
                                                ayurvedic.contraindications.forEach { c ->
                                                    Text("• $c", fontSize = 12.sp, color = Color(0xFF991B1B))
                                                }
                                            }
                                        }
                                    }

                                    // Disclaimer
                                    if (ayurvedic.disclaimer.isNotEmpty()) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Surface(
                                            modifier = Modifier.fillMaxWidth(),
                                            color = Color(0xFFFEF3C7),
                                            shape = RoundedCornerShape(6.dp)
                                        ) {
                                            Text(
                                                ayurvedic.disclaimer,
                                                fontSize = 11.sp,
                                                color = Color(0xFF92400E),
                                                modifier = Modifier.padding(8.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // (g) LLM-Powered Integrated Analysis
                item(key = "llm_analysis_section") {
                    response.llmAnalysis?.let { analysis ->
                        if (analysis.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(16.dp))
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F3FF)),
                                border = BorderStroke(1.dp, Color(0xFF8B5CF6))
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text(
                                        "AI-Powered Integrated Analysis",
                                        style = MaterialTheme.typography.titleMedium,
                                        color = Color(0xFF8B5CF6),
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        "Modern Medicine + Ayurvedic Wisdom",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color.Gray
                                    )
                                    Spacer(modifier = Modifier.height(12.dp))
                                    // Render markdown as simple text with basic formatting
                                    val lines = analysis.split("\n")
                                    lines.forEach { line ->
                                        when {
                                            line.startsWith("## ") -> {
                                                Spacer(modifier = Modifier.height(8.dp))
                                                Text(
                                                    line.removePrefix("## "),
                                                    fontWeight = FontWeight.Bold,
                                                    fontSize = 16.sp,
                                                    color = Color(0xFF8B5CF6)
                                                )
                                            }
                                            line.startsWith("### ") -> {
                                                Spacer(modifier = Modifier.height(6.dp))
                                                Text(
                                                    line.removePrefix("### "),
                                                    fontWeight = FontWeight.SemiBold,
                                                    fontSize = 14.sp
                                                )
                                            }
                                            line.startsWith("- ") -> {
                                                Text(
                                                    "• ${line.removePrefix("- ")}",
                                                    fontSize = 13.sp,
                                                    color = Color.DarkGray,
                                                    modifier = Modifier.padding(start = 8.dp)
                                                )
                                            }
                                            line.isNotBlank() -> {
                                                Text(
                                                    line.replace("**", "").replace("*", ""),
                                                    fontSize = 13.sp,
                                                    color = Color.DarkGray
                                                )
                                            }
                                            else -> Spacer(modifier = Modifier.height(4.dp))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // (h) Disclaimer
                if (response.disclaimer.isNotBlank()) {
                    item(key = "disclaimer") {
                        DisclaimerCard(text = response.disclaimer)
                    }
                }

                // Reset button
                item(key = "reset_button") {
                    OutlinedButton(
                        onClick = { viewModel.reset() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text("Start New Checkup")
                    }
                }
            }

            // Bottom spacer
            item(key = "bottom_spacer") {
                Spacer(Modifier.height(32.dp))
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 1: File Upload Card
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun FileUploadCard(
    selectedFileName: String?,
    selectedFileUri: Uri?,
    onPickFile: () -> Unit,
    onClear: () -> Unit,
    onExtract: () -> Unit,
    onUploadAndAnalyze: () -> Unit,
    canExtract: Boolean,
    canAnalyze: Boolean,
    isLoading: Boolean
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.Upload,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    text = "Upload Lab Report",
                    style = MaterialTheme.typography.titleLarge.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            // Supported formats note
            Surface(
                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Filled.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Supported formats: PDF, PNG, JPG, TXT",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            // File picker button
            OutlinedButton(
                onClick = onPickFile,
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading,
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(
                    imageVector = Icons.Filled.AttachFile,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (selectedFileName != null) "Change File" else "Select File"
                )
            }

            // Selected file info
            if (selectedFileName != null && selectedFileUri != null) {
                Surface(
                    color = Tertiary.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(
                                imageVector = Icons.Filled.Description,
                                contentDescription = null,
                                tint = Tertiary,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = selectedFileName,
                                    style = MaterialTheme.typography.bodyMedium.copy(
                                        fontWeight = FontWeight.Medium
                                    ),
                                    color = MaterialTheme.colorScheme.onSurface,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    text = "Ready for processing",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Tertiary
                                )
                            }
                        }
                        IconButton(
                            onClick = onClear,
                            enabled = !isLoading
                        ) {
                            Icon(
                                imageVector = Icons.Filled.Clear,
                                contentDescription = "Clear file",
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                // Action buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onExtract,
                        enabled = canExtract && !isLoading,
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = Secondary
                        )
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Analytics,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "Extract Values",
                            style = MaterialTheme.typography.labelLarge
                        )
                    }

                    Button(
                        onClick = onUploadAndAnalyze,
                        enabled = canAnalyze && !isLoading,
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary,
                            disabledContainerColor = MaterialTheme.colorScheme.primary
                                .copy(alpha = 0.3f),
                            disabledContentColor = MaterialTheme.colorScheme.onPrimary
                                .copy(alpha = 0.5f)
                        )
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Science,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "Upload & Analyse",
                            style = MaterialTheme.typography.labelLarge
                        )
                    }
                }

                // Hint when analyze is disabled
                if (!canAnalyze && canExtract) {
                    Text(
                        text = "Fill in age, sex, and region below to enable full analysis",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 2: Profile Card (collapsible)
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProfileCard(
    expanded: Boolean,
    onToggleExpanded: () -> Unit,
    age: String,
    onAgeChange: (String) -> Unit,
    isAgeValid: Boolean,
    selectedSex: String,
    onSexChange: (String) -> Unit,
    sexDropdownExpanded: Boolean,
    onSexDropdownExpandedChange: (Boolean) -> Unit,
    selectedRegion: String,
    onRegionChange: (String) -> Unit,
    regionDropdownExpanded: Boolean,
    onRegionDropdownExpandedChange: (Boolean) -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            // Header (always visible, clickable to toggle)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onToggleExpanded() }
                    .padding(20.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Filled.Person,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text(
                            text = "Profile Information",
                            style = MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        if (!expanded && age.isNotBlank()) {
                            Text(
                                text = buildString {
                                    append("Age: $age")
                                    if (selectedSex.isNotBlank()) append(" | $selectedSex")
                                    if (selectedRegion.isNotBlank()) append(" | $selectedRegion")
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }
                Icon(
                    imageVector = if (expanded) Icons.Filled.ExpandLess
                    else Icons.Filled.ExpandMore,
                    contentDescription = if (expanded) "Collapse" else "Expand",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Collapsible content
            AnimatedVisibility(
                visible = expanded,
                enter = expandVertically() + fadeIn(),
                exit = shrinkVertically() + fadeOut()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(start = 20.dp, end = 20.dp, bottom = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    HorizontalDivider(
                        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                    )

                    // ── Age ──────────────────────────────────────────────
                    OutlinedTextField(
                        value = age,
                        onValueChange = onAgeChange,
                        label = { Text("Age") },
                        placeholder = { Text("Enter your age") },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Number
                        ),
                        singleLine = true,
                        isError = !isAgeValid,
                        supportingText = if (!isAgeValid) {
                            { Text("Age must be between 1 and 120") }
                        } else {
                            null
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = checkupTextFieldColors()
                    )

                    // ── Sex Dropdown ─────────────────────────────────────
                    ExposedDropdownMenuBox(
                        expanded = sexDropdownExpanded,
                        onExpandedChange = onSexDropdownExpandedChange
                    ) {
                        OutlinedTextField(
                            value = selectedSex.replaceFirstChar {
                                if (it.isLowerCase()) it.titlecase() else it.toString()
                            },
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Sex") },
                            placeholder = { Text("Select sex") },
                            trailingIcon = {
                                ExposedDropdownMenuDefaults.TrailingIcon(
                                    expanded = sexDropdownExpanded
                                )
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                            colors = checkupTextFieldColors()
                        )

                        ExposedDropdownMenu(
                            expanded = sexDropdownExpanded,
                            onDismissRequest = { onSexDropdownExpandedChange(false) }
                        ) {
                            sexOptions.forEach { sex ->
                                DropdownMenuItem(
                                    text = {
                                        Text(
                                            text = sex.replaceFirstChar {
                                                if (it.isLowerCase()) it.titlecase()
                                                else it.toString()
                                            },
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                    },
                                    onClick = {
                                        onSexChange(sex)
                                        onSexDropdownExpandedChange(false)
                                    },
                                    contentPadding = ExposedDropdownMenuDefaults.ItemContentPadding
                                )
                            }
                        }
                    }

                    // ── Region Dropdown ──────────────────────────────────
                    ExposedDropdownMenuBox(
                        expanded = regionDropdownExpanded,
                        onExpandedChange = onRegionDropdownExpandedChange
                    ) {
                        OutlinedTextField(
                            value = selectedRegion,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Region / Ancestry") },
                            placeholder = { Text("Select region") },
                            trailingIcon = {
                                ExposedDropdownMenuDefaults.TrailingIcon(
                                    expanded = regionDropdownExpanded
                                )
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                            colors = checkupTextFieldColors()
                        )

                        ExposedDropdownMenu(
                            expanded = regionDropdownExpanded,
                            onDismissRequest = { onRegionDropdownExpandedChange(false) }
                        ) {
                            healthCheckupRegions.forEach { region ->
                                DropdownMenuItem(
                                    text = {
                                        Text(
                                            text = region,
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                    },
                                    onClick = {
                                        onRegionChange(region)
                                        onRegionDropdownExpandedChange(false)
                                    },
                                    contentPadding = ExposedDropdownMenuDefaults.ItemContentPadding
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Loading Indicator
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun LoadingIndicator(message: String) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            CircularProgressIndicator(
                color = MaterialTheme.colorScheme.primary,
                strokeWidth = 3.dp,
                modifier = Modifier.size(48.dp)
            )
            Text(
                text = message,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 3: Extraction Preview
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExtractionPreviewSection(
    preview: ReportParsePreview,
    onProceedToAnalyze: () -> Unit,
    canAnalyze: Boolean
) {
    var showUnrecognized by remember { mutableStateOf(false) }

    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.CheckCircle,
                    contentDescription = null,
                    tint = Tertiary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    text = "Extraction Preview",
                    style = MaterialTheme.typography.titleLarge.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            // Confidence badge
            val confidencePct = (preview.confidence * 100).toInt()
            val confidenceColor = when {
                confidencePct >= 60 -> RiskLow
                confidencePct >= 30 -> WarningAmber
                else -> RiskHigh
            }
            Surface(
                color = confidenceColor.copy(alpha = 0.15f),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(confidenceColor, CircleShape)
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Confidence: $confidencePct%",
                        style = MaterialTheme.typography.labelLarge.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = confidenceColor
                    )
                    Spacer(Modifier.width(12.dp))
                    Text(
                        text = "File type: ${preview.fileType}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Count summary
            val bloodCount = preview.extractedBloodTests.size
            val urineCount = preview.extractedUrineTests.size
            Surface(
                color = SurfaceVariant,
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "$bloodCount",
                            style = MaterialTheme.typography.headlineMedium.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = Primary
                        )
                        Text(
                            text = "Blood values",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "$urineCount",
                            style = MaterialTheme.typography.headlineMedium.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = Secondary
                        )
                        Text(
                            text = "Urine values",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "${preview.textLength}",
                            style = MaterialTheme.typography.headlineMedium.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = Tertiary
                        )
                        Text(
                            text = "Characters",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Extracted values table
            if (preview.extractedBloodTests.isNotEmpty() ||
                preview.extractedUrineTests.isNotEmpty()
            ) {
                ExtractedValuesTable(
                    bloodTests = preview.extractedBloodTests,
                    urineTests = preview.extractedUrineTests
                )
            }

            // Abdomen notes
            if (preview.extractedAbdomenNotes.isNotBlank()) {
                Surface(
                    color = WarningAmber.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = "Abdomen Notes",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = WarningAmber
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = preview.extractedAbdomenNotes,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            // Unrecognized lines (expandable)
            if (preview.unrecognizedLines.isNotEmpty()) {
                Column(
                    modifier = Modifier.animateContentSize()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showUnrecognized = !showUnrecognized }
                            .padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "${preview.unrecognizedLines.size} unrecognized lines",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = if (showUnrecognized) "Hide" else "Show",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    if (showUnrecognized) {
                        Surface(
                            color = MaterialTheme.colorScheme.outline.copy(alpha = 0.08f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Column(
                                modifier = Modifier.padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                preview.unrecognizedLines.forEach { line ->
                                    Text(
                                        text = line,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                            .copy(alpha = 0.7f),
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Proceed to Analyse button
            Button(
                onClick = onProceedToAnalyze,
                enabled = canAnalyze,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    disabledContainerColor = MaterialTheme.colorScheme.primary
                        .copy(alpha = 0.3f),
                    disabledContentColor = MaterialTheme.colorScheme.onPrimary
                        .copy(alpha = 0.5f)
                )
            ) {
                Icon(
                    imageVector = Icons.Filled.Science,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = "Proceed to Analyse",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold
                    )
                )
            }

            if (!canAnalyze) {
                Text(
                    text = "Please fill in age, sex, and region in the profile section above",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

/**
 * Table showing extracted blood and urine test values from the parse preview.
 */
@Composable
private fun ExtractedValuesTable(
    bloodTests: Map<String, Double>,
    urineTests: Map<String, Double>
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = "Extracted Values",
                style = MaterialTheme.typography.titleSmall.copy(
                    fontWeight = FontWeight.SemiBold
                ),
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.height(8.dp))

            // Table header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .background(
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.15f),
                        RoundedCornerShape(6.dp)
                    )
                    .padding(horizontal = 10.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Parameter",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(140.dp)
                )
                Text(
                    text = "Value",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(80.dp)
                )
                Text(
                    text = "Panel",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(60.dp)
                )
            }

            // Blood test rows
            bloodTests.forEach { (name, value) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 10.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = name,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.width(140.dp),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = String.format("%.2f", value),
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontWeight = FontWeight.Medium
                        ),
                        color = Primary,
                        modifier = Modifier.width(80.dp)
                    )
                    Surface(
                        color = Primary.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(4.dp),
                        modifier = Modifier.width(60.dp)
                    ) {
                        Text(
                            text = "Blood",
                            style = MaterialTheme.typography.labelSmall,
                            color = Primary,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(
                                horizontal = 6.dp,
                                vertical = 2.dp
                            )
                        )
                    }
                }
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                )
            }

            // Urine test rows
            urineTests.forEach { (name, value) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 10.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = name,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.width(140.dp),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = String.format("%.2f", value),
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontWeight = FontWeight.Medium
                        ),
                        color = Secondary,
                        modifier = Modifier.width(80.dp)
                    )
                    Surface(
                        color = Secondary.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(4.dp),
                        modifier = Modifier.width(60.dp)
                    ) {
                        Text(
                            text = "Urine",
                            style = MaterialTheme.typography.labelSmall,
                            color = Secondary,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(
                                horizontal = 6.dp,
                                vertical = 2.dp
                            )
                        )
                    }
                }
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                )
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5a: Health Score Card
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun HealthScoreCard(
    score: Double,
    breakdown: Map<String, Double>,
    totalTested: Int,
    abnormalCount: Int
) {
    val scoreInt = score.toInt().coerceIn(0, 100)
    val scoreColor = when {
        scoreInt >= 80 -> RiskLow
        scoreInt >= 60 -> Tertiary
        scoreInt >= 40 -> WarningAmber
        scoreInt >= 20 -> RiskModerate
        else -> RiskHigh
    }

    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 3.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Overall Health Score",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(Modifier.height(16.dp))

            // Circular score display
            Box(
                modifier = Modifier.size(160.dp),
                contentAlignment = Alignment.Center
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val strokeWidth = 12.dp.toPx()
                    val radius = (size.minDimension - strokeWidth) / 2f
                    val topLeft = Offset(
                        (size.width - radius * 2) / 2f,
                        (size.height - radius * 2) / 2f
                    )
                    val arcSize = Size(radius * 2, radius * 2)

                    // Background track
                    drawArc(
                        color = scoreColor.copy(alpha = 0.15f),
                        startAngle = -90f,
                        sweepAngle = 360f,
                        useCenter = false,
                        topLeft = topLeft,
                        size = arcSize,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )

                    // Score arc
                    drawArc(
                        color = scoreColor,
                        startAngle = -90f,
                        sweepAngle = 360f * (scoreInt / 100f),
                        useCenter = false,
                        topLeft = topLeft,
                        size = arcSize,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                }

                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$scoreInt",
                        style = MaterialTheme.typography.displayLarge.copy(
                            fontSize = 48.sp,
                            fontWeight = FontWeight.Bold
                        ),
                        color = scoreColor
                    )
                    Text(
                        text = "/ 100",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Parameters tested / abnormal count
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$totalTested",
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = Primary
                    )
                    Text(
                        text = "Tested",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$abnormalCount",
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = if (abnormalCount > 0) RiskHigh else RiskLow
                    )
                    Text(
                        text = "Abnormal",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "${totalTested - abnormalCount}",
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = RiskLow
                    )
                    Text(
                        text = "Normal",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Score breakdown chips by category
            if (breakdown.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                )
                Spacer(Modifier.height(12.dp))

                Text(
                    text = "Score Breakdown",
                    style = MaterialTheme.typography.labelMedium.copy(
                        fontWeight = FontWeight.SemiBold
                    ),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(8.dp))

                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    breakdown.forEach { (category, categoryScore) ->
                        val catScoreInt = categoryScore.toInt().coerceIn(0, 100)
                        val catColor = when {
                            catScoreInt >= 80 -> RiskLow
                            catScoreInt >= 60 -> Tertiary
                            catScoreInt >= 40 -> WarningAmber
                            else -> RiskHigh
                        }
                        Surface(
                            color = catColor.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(
                                    horizontal = 12.dp,
                                    vertical = 6.dp
                                ),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = category,
                                    style = MaterialTheme.typography.labelMedium,
                                    color = catColor
                                )
                                Spacer(Modifier.width(6.dp))
                                Text(
                                    text = "$catScoreInt",
                                    style = MaterialTheme.typography.labelMedium.copy(
                                        fontWeight = FontWeight.Bold
                                    ),
                                    color = catColor
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5b: Lab Results Table Card
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun LabResultsTableCard(labResults: List<LabResultItem>) {
    // Group by category
    val grouped = labResults.groupBy { it.category }

    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            grouped.forEach { (category, items) ->
                // Category header
                Surface(
                    color = Primary.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                ) {
                    Text(
                        text = category,
                        style = MaterialTheme.typography.titleSmall.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = Primary,
                        modifier = Modifier.padding(
                            horizontal = 10.dp,
                            vertical = 6.dp
                        )
                    )
                }

                // Table header
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 6.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    LabTableHeaderCell("Parameter", Modifier.width(110.dp))
                    LabTableHeaderCell("Value", Modifier.width(60.dp))
                    LabTableHeaderCell("Unit", Modifier.width(50.dp))
                    LabTableHeaderCell("Reference", Modifier.width(90.dp))
                    LabTableHeaderCell("Status", Modifier.width(70.dp))
                }

                // Table rows
                items.forEach { item ->
                    val statusColor = labStatusColor(item.status)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(horizontal = 6.dp, vertical = 5.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = item.displayName,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.width(110.dp),
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = String.format("%.1f", item.value),
                            style = MaterialTheme.typography.bodySmall.copy(
                                fontWeight = FontWeight.Medium
                            ),
                            color = statusColor,
                            modifier = Modifier.width(60.dp)
                        )
                        Text(
                            text = item.unit,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.width(50.dp),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "${String.format("%.1f", item.referenceLow)} - ${
                                String.format("%.1f", item.referenceHigh)
                            }",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.width(90.dp)
                        )
                        Surface(
                            color = statusColor.copy(alpha = 0.15f),
                            shape = RoundedCornerShape(4.dp),
                            modifier = Modifier.width(70.dp)
                        ) {
                            Text(
                                text = item.status.replaceFirstChar {
                                    if (it.isLowerCase()) it.titlecase()
                                    else it.toString()
                                },
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold
                                ),
                                color = statusColor,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(
                                    horizontal = 6.dp,
                                    vertical = 3.dp
                                )
                            )
                        }
                    }
                    HorizontalDivider(
                        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                    )
                }

                Spacer(Modifier.height(8.dp))
            }
        }
    }
}

@Composable
private fun LabTableHeaderCell(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelSmall.copy(
            fontWeight = FontWeight.Bold
        ),
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier
    )
}

/** Maps a lab result status string to a traffic-light colour. */
private fun labStatusColor(status: String): Color = when (status.lowercase()) {
    "normal" -> RiskLow
    "high", "low" -> WarningAmber
    "critical", "critical_high", "critical_low" -> RiskHigh
    else -> Color(0xFFBDBDBD)
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5c: Health Finding Card
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun HealthFindingCard(finding: HealthFindingItem) {
    var expanded by remember { mutableStateOf(false) }

    val severityColor = when (finding.severity.lowercase()) {
        "mild" -> WarningAmber
        "moderate" -> RiskModerate
        "severe", "critical" -> RiskHigh
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(),
        colors = CardDefaults.elevatedCardColors(containerColor = SurfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header row: condition name + severity badge
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { expanded = !expanded },
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(
                        imageVector = Icons.Filled.Healing,
                        contentDescription = null,
                        tint = severityColor,
                        modifier = Modifier.size(22.dp)
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = finding.displayName,
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Spacer(Modifier.width(8.dp))

                Surface(
                    color = severityColor.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(
                        text = finding.severity.replaceFirstChar {
                            if (it.isLowerCase()) it.titlecase()
                            else it.toString()
                        },
                        modifier = Modifier.padding(
                            horizontal = 10.dp,
                            vertical = 4.dp
                        ),
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = severityColor
                    )
                }

                Spacer(Modifier.width(4.dp))

                Icon(
                    imageVector = if (expanded) Icons.Filled.ExpandLess
                    else Icons.Filled.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Expanded content
            if (expanded) {
                Spacer(Modifier.height(12.dp))
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                )
                Spacer(Modifier.height(12.dp))

                // Evidence list
                if (finding.evidence.isNotEmpty()) {
                    Text(
                        text = "Evidence",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(4.dp))
                    finding.evidence.forEach { evidence ->
                        Row(
                            modifier = Modifier.padding(vertical = 2.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Box(
                                modifier = Modifier
                                    .padding(top = 6.dp)
                                    .size(5.dp)
                                    .background(
                                        severityColor.copy(alpha = 0.7f),
                                        CircleShape
                                    )
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = evidence,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }

                // Dietary impact
                if (finding.dietaryImpact.isNotBlank()) {
                    Text(
                        text = "Dietary Impact",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = finding.dietaryImpact,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(Modifier.height(8.dp))
                }

                // Foods to increase
                if (finding.foodsToIncrease.isNotEmpty()) {
                    Text(
                        text = "Foods to Increase",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = RiskLow
                    )
                    Spacer(Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        finding.foodsToIncrease.forEach { food ->
                            Surface(
                                color = RiskLow.copy(alpha = 0.12f),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    text = food,
                                    modifier = Modifier.padding(
                                        horizontal = 10.dp,
                                        vertical = 4.dp
                                    ),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = RiskLow
                                )
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }

                // Foods to avoid
                if (finding.foodsToAvoid.isNotEmpty()) {
                    Text(
                        text = "Foods to Avoid",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = RiskHigh
                    )
                    Spacer(Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        finding.foodsToAvoid.forEach { food ->
                            Surface(
                                color = RiskHigh.copy(alpha = 0.12f),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    text = food,
                                    modifier = Modifier.padding(
                                        horizontal = 10.dp,
                                        vertical = 4.dp
                                    ),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = RiskHigh
                                )
                            }
                        }
                    }
                }

                // Nutrients to increase / decrease
                if (finding.nutrientsToIncrease.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "Nutrients to Increase",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = Tertiary
                    )
                    Spacer(Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        finding.nutrientsToIncrease.forEach { nutrient ->
                            Surface(
                                color = Tertiary.copy(alpha = 0.12f),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    text = nutrient,
                                    modifier = Modifier.padding(
                                        horizontal = 10.dp,
                                        vertical = 4.dp
                                    ),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Tertiary
                                )
                            }
                        }
                    }
                }

                if (finding.nutrientsToDecrease.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "Nutrients to Decrease",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = RiskModerate
                    )
                    Spacer(Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        finding.nutrientsToDecrease.forEach { nutrient ->
                            Surface(
                                color = RiskModerate.copy(alpha = 0.12f),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    text = nutrient,
                                    modifier = Modifier.padding(
                                        horizontal = 10.dp,
                                        vertical = 4.dp
                                    ),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = RiskModerate
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5d: Detected Conditions Chips
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DetectedConditionsChips(conditions: List<String>) {
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        conditions.forEach { condition ->
            Surface(
                color = RiskModerate.copy(alpha = 0.12f),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    modifier = Modifier.padding(
                        horizontal = 14.dp,
                        vertical = 8.dp
                    ),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Filled.Warning,
                        contentDescription = null,
                        tint = RiskModerate,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = condition,
                        style = MaterialTheme.typography.labelLarge.copy(
                            fontWeight = FontWeight.Medium
                        ),
                        color = RiskModerate
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5e: Diet Recommendation Card
// ═════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DietRecommendationCard(diet: DietRecommendation) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
                .animateContentSize(),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Summary
            Text(
                text = diet.summary,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )

            // Calorie target
            if (diet.calorieTarget != null) {
                ElevatedCard(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.elevatedCardColors(
                        containerColor = SurfaceVariant
                    )
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
                            style = MaterialTheme.typography.titleLarge.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = Primary
                        )
                    }
                }
            }

            // Key nutrients as chips
            if (diet.keyNutrients.isNotEmpty()) {
                Text(
                    text = "Key Nutrients",
                    style = MaterialTheme.typography.labelMedium.copy(
                        fontWeight = FontWeight.SemiBold
                    ),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    diet.keyNutrients.forEach { nutrient ->
                        Surface(
                            color = Tertiary.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text(
                                text = nutrient,
                                modifier = Modifier.padding(
                                    horizontal = 12.dp,
                                    vertical = 6.dp
                                ),
                                style = MaterialTheme.typography.labelMedium.copy(
                                    fontWeight = FontWeight.Medium
                                ),
                                color = Tertiary
                            )
                        }
                    }
                }
            }

            // Foods to increase
            if (diet.foodsToIncrease.isNotEmpty()) {
                DietFoodList(
                    title = "Foods to Increase",
                    items = diet.foodsToIncrease,
                    tintColor = RiskLow
                )
            }

            // Foods to avoid
            if (diet.foodsToAvoid.isNotEmpty()) {
                DietFoodList(
                    title = "Foods to Avoid",
                    items = diet.foodsToAvoid,
                    tintColor = RiskHigh
                )
            }

            // Meal plans (expandable per day)
            if (diet.mealPlans.isNotEmpty()) {
                HorizontalDivider(
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                    modifier = Modifier.padding(vertical = 4.dp)
                )
                Text(
                    text = "Meal Plans",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.SemiBold
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )
                diet.mealPlans.forEach { plan ->
                    MealPlanCard(mealPlan = plan)
                }
            }
        }
    }
}

@Composable
private fun DietFoodList(
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
                style = MaterialTheme.typography.labelMedium.copy(
                    fontWeight = FontWeight.Bold
                ),
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
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section 5f: Disclaimer Card
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun DisclaimerCard(text: String) {
    Column(modifier = Modifier.padding(top = 8.dp)) {
        HorizontalDivider(
            color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
        )
        Spacer(Modifier.height(12.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp),
            verticalAlignment = Alignment.Top
        ) {
            Icon(
                imageVector = Icons.Filled.Warning,
                contentDescription = "Disclaimer",
                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                modifier = Modifier
                    .padding(top = 2.dp, end = 8.dp)
                    .size(16.dp)
            )
            Text(
                text = text,
                style = MaterialTheme.typography.labelMedium.copy(
                    fontSize = 11.sp,
                    lineHeight = 16.sp
                ),
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                textAlign = TextAlign.Start
            )
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Error Card
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun ErrorCard(
    errorMessage: String,
    onRetry: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Outlined.ErrorOutline,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.size(28.dp)
                )
                Text(
                    text = "Something went wrong",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.SemiBold
                    ),
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }

            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onErrorContainer
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(
                    onClick = onDismiss,
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.onErrorContainer
                    )
                ) {
                    Text("Dismiss")
                }

                Spacer(Modifier.width(8.dp))

                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError
                    )
                ) {
                    Text("Retry")
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Section Header
// ═════════════════════════════════════════════════════════════════════════════

@Composable
private fun CheckupSectionHeader(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    color: Color = MaterialTheme.colorScheme.primary
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(bottom = 8.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(26.dp)
            )
            Spacer(Modifier.width(10.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall.copy(
                    fontWeight = FontWeight.Bold
                ),
                color = color
            )
        }
        HorizontalDivider(
            color = color.copy(alpha = 0.4f),
            thickness = 1.dp,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// Shared style helpers
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Consistent [OutlinedTextField] colours for the health checkup screen.
 */
@Composable
private fun checkupTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = MaterialTheme.colorScheme.onSurface,
    unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    focusedBorderColor = MaterialTheme.colorScheme.primary,
    unfocusedBorderColor = MaterialTheme.colorScheme.outline,
    cursorColor = MaterialTheme.colorScheme.primary,
    focusedLabelColor = MaterialTheme.colorScheme.primary,
    unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
    focusedPlaceholderColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
    unfocusedPlaceholderColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
    errorBorderColor = MaterialTheme.colorScheme.error,
    errorLabelColor = MaterialTheme.colorScheme.error,
    errorSupportingTextColor = MaterialTheme.colorScheme.error
)
