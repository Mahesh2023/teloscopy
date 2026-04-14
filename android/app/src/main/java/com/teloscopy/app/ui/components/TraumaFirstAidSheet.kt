package com.teloscopy.app.ui.components

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.SaveAlt
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Sms
import androidx.compose.material.icons.filled.VolunteerActivism
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// ── Coral / warm theme palette ───────────────────────────────────────────────
private val CoralPrimary = Color(0xFFFF6B6B)
private val AccentAmber = Color(0xFFFFA726)
private val SurfaceDark = Color(0xFF1A1220)
private val BackgroundDark = Color(0xFF0F0A14)
private val TextPrimary = Color(0xFFE0E0E0)
private val TextSecondary = Color(0xFFBDBDBD)
private val CardBorder = Color(0xFF2A1F30)

// ── Data classes ─────────────────────────────────────────────────────────────

private data class CrisisHotline(
    val name: String,
    val number: String,
    val description: String,
    val hours: String,
    val region: String,
    val textNumber: String? = null,
    val isEmergency: Boolean = false
)

private data class GroundingStep(
    val count: Int,
    val sense: String,
    val instruction: String,
    val examples: String,
    val color: Color
)

private data class SafetyPlanStep(
    val stepNumber: Int,
    val title: String,
    val prompt: String,
    val examples: List<String>
)

private data class LeapStep(
    val letter: String,
    val name: String,
    val description: String
)

// ── Main composable ──────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TraumaFirstAidSheet(
    isVisible: Boolean,
    onDismiss: () -> Unit,
    crisisSeverity: String? = null
) {
    if (!isVisible) return

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var selectedTab by remember { mutableIntStateOf(0) }

    LaunchedEffect(crisisSeverity) {
        if (crisisSeverity == "high") {
            selectedTab = 0
        }
    }

    val tabItems = listOf(
        "Crisis Lines" to Icons.Filled.Phone,
        "Grounding" to Icons.Filled.SelfImprovement,
        "Safety Plan" to Icons.Filled.Shield,
        "De-escalation" to Icons.Filled.VolunteerActivism,
        "Learn" to Icons.Filled.MenuBook
    )

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = BackgroundDark,
        dragHandle = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .width(40.dp)
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(TextSecondary.copy(alpha = 0.4f))
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Trauma First Aid",
                    color = CoralPrimary,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Support resources and coping tools",
                    color = TextSecondary,
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
            }
        }
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            ScrollableTabRow(
                selectedTabIndex = selectedTab,
                containerColor = SurfaceDark,
                contentColor = CoralPrimary,
                edgePadding = 8.dp,
                indicator = {},
                divider = { HorizontalDivider(color = CardBorder, thickness = 1.dp) }
            ) {
                tabItems.forEachIndexed { index, (title, icon) ->
                    val selected = selectedTab == index
                    val tabColor by animateColorAsState(
                        targetValue = if (selected) CoralPrimary else TextSecondary.copy(alpha = 0.5f),
                        label = "tabColor"
                    )
                    Tab(
                        selected = selected,
                        onClick = { selectedTab = index },
                        text = {
                            Text(
                                text = title,
                                color = tabColor,
                                fontSize = 12.sp,
                                fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        icon = {
                            Icon(
                                imageVector = icon,
                                contentDescription = title,
                                tint = tabColor,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    )
                }
            }

            when (selectedTab) {
                0 -> CrisisLinesTab(highlightEmergency = crisisSeverity == "high")
                1 -> GroundingTab()
                2 -> SafetyPlanTab()
                3 -> DeEscalationTab()
                4 -> LearnTab()
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 1 — CRISIS LINES
// ═══════════════════════════════════════════════════════════════════════════════

@Composable
private fun CrisisLinesTab(highlightEmergency: Boolean) {
    val context = LocalContext.current

    val hotlines = remember {
        listOf(
            CrisisHotline(
                name = "Emergency Services (India)",
                number = "112",
                description = "India's unified emergency number — also 108 (ambulance) or 100 (police)",
                hours = "24/7",
                region = "India",
                isEmergency = true
            ),
            CrisisHotline(
                name = "Vandrevala Foundation Helpline",
                number = "1860-2662-345",
                description = "Free, confidential 24/7 mental health support across India",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "iCall (TISS) Helpline",
                number = "9152987821",
                description = "Mon-Sat 8am-10pm IST — emotional support & crisis intervention (TISS)",
                hours = "Mon-Sat 8am-10pm IST",
                region = "India"
            ),
            CrisisHotline(
                name = "AASRA",
                number = "9820466726",
                description = "24/7 crisis intervention for the suicidal & despairing (Mumbai)",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "KIRAN Mental Health Helpline",
                number = "1800-599-0019",
                description = "Govt of India 24/7 toll-free helpline for mental health support",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "Women Helpline (NCW)",
                number = "7827-170-170",
                description = "National Commission for Women helpline for women in distress.",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "One Stop Centre",
                number = "181",
                description = "Women affected by violence — integrated support (medical, legal, counselling).",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "CHILDLINE India",
                number = "1098",
                description = "24/7 helpline for children in need of care and protection.",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "Snehi",
                number = "044-24640050",
                description = "Emotional support and crisis intervention helpline based in Chennai.",
                hours = "24/7",
                region = "India"
            ),
            CrisisHotline(
                name = "NIMHANS Helpline",
                number = "080-46110007",
                description = "India's premier mental health institution — psychosocial support & referrals.",
                hours = "Mon-Sat 9:30am-4:30pm IST",
                region = "India"
            ),
            CrisisHotline(
                name = "Roshni Trust",
                number = "040-66202000",
                description = "Hyderabad-based counselling for depression, suicidal feelings, and distress.",
                hours = "11am-9pm IST, Mon-Sat",
                region = "India"
            ),
            CrisisHotline(
                name = "Drug De-addiction Helpline",
                number = "1800-11-0031",
                description = "Govt of India toll-free helpline for substance abuse & de-addiction support.",
                hours = "24/7",
                region = "India"
            )
        )
    }

    val regions = remember { hotlines.map { it.region }.distinct() }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Text(
                text = "If you or someone you know is in immediate danger, please call emergency services.",
                color = CoralPrimary.copy(alpha = 0.9f),
                fontSize = 13.sp,
                fontStyle = FontStyle.Italic,
                modifier = Modifier.padding(bottom = 4.dp)
            )
        }

        regions.forEach { region ->
            item {
                Text(
                    text = region,
                    color = AccentAmber,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp, bottom = 4.dp)
                )
            }
            items(hotlines.filter { it.region == region }) { hotline ->
                CrisisHotlineCard(
                    hotline = hotline,
                    highlight = highlightEmergency && (hotline.number == "1860-2662-345" || hotline.isEmergency),
                    context = context
                )
            }
        }

        item { Spacer(modifier = Modifier.height(32.dp)) }
    }
}

@Composable
private fun CrisisHotlineCard(
    hotline: CrisisHotline,
    highlight: Boolean,
    context: Context
) {
    val borderColor = when {
        hotline.isEmergency -> Color(0xFFFF1744)
        highlight -> CoralPrimary
        else -> CardBorder
    }
    val bgColor = if (hotline.isEmergency) Color(0xFF2A0A0A) else SurfaceDark

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderColor, RoundedCornerShape(16.dp)),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = bgColor)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = hotline.name,
                        color = TextPrimary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (hotline.isEmergency) {
                        Text(
                            text = "EMERGENCY",
                            color = Color(0xFFFF1744),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                Row {
                    IconButton(
                        onClick = {
                            val dialIntent = Intent(
                                Intent.ACTION_DIAL,
                                Uri.parse("tel:${hotline.number.replace(" ", "")}")
                            )
                            context.startActivity(dialIntent)
                        },
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(CoralPrimary.copy(alpha = 0.15f))
                    ) {
                        Icon(
                            Icons.Filled.Call,
                            contentDescription = "Call ${hotline.name}",
                            tint = CoralPrimary,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    if (hotline.textNumber != null) {
                        Spacer(modifier = Modifier.width(8.dp))
                        IconButton(
                            onClick = {
                                val smsIntent = Intent(
                                    Intent.ACTION_SENDTO,
                                    Uri.parse("smsto:${hotline.textNumber}")
                                )
                                context.startActivity(smsIntent)
                            },
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(AccentAmber.copy(alpha = 0.15f))
                        ) {
                            Icon(
                                Icons.Filled.Sms,
                                contentDescription = "Text ${hotline.name}",
                                tint = AccentAmber,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = hotline.number,
                color = CoralPrimary,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.clickable {
                    val dialIntent = Intent(
                        Intent.ACTION_DIAL,
                        Uri.parse("tel:${hotline.number.replace(" ", "")}")
                    )
                    context.startActivity(dialIntent)
                }
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = hotline.description,
                color = TextSecondary,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = hotline.hours,
                color = AccentAmber.copy(alpha = 0.8f),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 2 — GROUNDING
// ═══════════════════════════════════════════════════════════════════════════════

@Composable
private fun GroundingTab() {
    var activeSection by remember { mutableIntStateOf(0) }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf("5-4-3-2-1", "Breathing", "Butterfly Hug", "Body Scan").forEachIndexed { index, label ->
                    AssistChip(
                        onClick = { activeSection = index },
                        label = {
                            Text(
                                label,
                                fontSize = 12.sp,
                                fontWeight = if (activeSection == index) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = if (activeSection == index) CoralPrimary.copy(alpha = 0.2f) else SurfaceDark,
                            labelColor = if (activeSection == index) CoralPrimary else TextSecondary
                        ),
                        border = AssistChipDefaults.assistChipBorder(
                            borderColor = if (activeSection == index) CoralPrimary else CardBorder,
                            enabled = true
                        )
                    )
                }
            }
        }

        when (activeSection) {
            0 -> item { FiveFourThreeTwoOneExercise() }
            1 -> item { BoxBreathingTimer() }
            2 -> item { ButterflyHugSection() }
            3 -> item { BodyScanSection() }
        }

        item { Spacer(modifier = Modifier.height(32.dp)) }
    }
}

@Composable
private fun FiveFourThreeTwoOneExercise() {
    var currentStep by remember { mutableIntStateOf(0) }

    val steps = remember {
        listOf(
            GroundingStep(5, "See", "Name 5 things you can see right now.", "A clock, your hands, a window, a book, a plant", Color(0xFFEF5350)),
            GroundingStep(4, "Touch", "Name 4 things you can physically feel.", "The chair beneath you, your feet on the floor, fabric on your skin, warmth of your hands", Color(0xFFFFA726)),
            GroundingStep(3, "Hear", "Name 3 things you can hear.", "Traffic outside, the hum of a fan, birds chirping", Color(0xFF66BB6A)),
            GroundingStep(2, "Smell", "Name 2 things you can smell.", "Fresh air, coffee, laundry detergent", Color(0xFF42A5F5)),
            GroundingStep(1, "Taste", "Name 1 thing you can taste.", "Toothpaste, water, a recent meal", Color(0xFFAB47BC))
        )
    }

    Column {
        Text(
            text = "5-4-3-2-1 Grounding Exercise",
            color = CoralPrimary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "This technique helps bring you back to the present moment using your five senses.",
            color = TextSecondary,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        Spacer(modifier = Modifier.height(16.dp))

        steps.forEachIndexed { index, step ->
            AnimatedVisibility(
                visible = index <= currentStep,
                enter = expandVertically(animationSpec = tween(400)),
                exit = shrinkVertically()
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 10.dp)
                        .border(1.dp, step.color.copy(alpha = 0.4f), RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceDark)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .clip(CircleShape)
                                .background(step.color.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "${step.count}",
                                color = step.color,
                                fontSize = 22.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.width(14.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = step.sense,
                                color = step.color,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = step.instruction,
                                color = TextPrimary,
                                fontSize = 14.sp,
                                lineHeight = 20.sp
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "e.g. ${step.examples}",
                                color = TextSecondary.copy(alpha = 0.7f),
                                fontSize = 12.sp,
                                fontStyle = FontStyle.Italic,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            if (currentStep > 0) {
                Button(
                    onClick = { currentStep-- },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = SurfaceDark,
                        contentColor = TextPrimary
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Back")
                }
            } else {
                Spacer(modifier = Modifier.width(1.dp))
            }

            if (currentStep < steps.size - 1) {
                Button(
                    onClick = { currentStep++ },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = CoralPrimary,
                        contentColor = Color.White
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Next")
                }
            } else {
                Button(
                    onClick = { currentStep = 0 },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AccentAmber,
                        contentColor = Color.Black
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Restart")
                }
            }
        }
    }
}

@Composable
private fun BoxBreathingTimer() {
    var isRunning by remember { mutableStateOf(false) }
    var phaseIndex by remember { mutableIntStateOf(0) }
    var countdown by remember { mutableIntStateOf(4) }
    var cycleCount by remember { mutableIntStateOf(0) }

    val phases = remember { listOf("Inhale", "Hold", "Exhale", "Hold") }
    val phaseColors = remember {
        listOf(
            Color(0xFF42A5F5),
            Color(0xFF66BB6A),
            Color(0xFFFFA726),
            Color(0xFFAB47BC)
        )
    }

    val breathScale by animateFloatAsState(
        targetValue = when {
            !isRunning -> 0.6f
            phases[phaseIndex] == "Inhale" -> 1.0f
            phases[phaseIndex] == "Exhale" -> 0.4f
            else -> if (phaseIndex == 1) 1.0f else 0.4f
        },
        animationSpec = tween(durationMillis = if (isRunning) 900 else 300),
        label = "breathScale"
    )

    LaunchedEffect(isRunning) {
        if (isRunning) {
            while (isRunning) {
                delay(1000L)
                countdown--
                if (countdown <= 0) {
                    countdown = 4
                    phaseIndex = (phaseIndex + 1) % 4
                    if (phaseIndex == 0) cycleCount++
                }
            }
        } else {
            phaseIndex = 0
            countdown = 4
        }
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = "Box Breathing",
            color = CoralPrimary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "A calming technique used by Navy SEALs. Breathe in a square pattern: 4 seconds each phase.",
            color = TextSecondary,
            fontSize = 13.sp,
            lineHeight = 18.sp,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(24.dp))

        Box(
            modifier = Modifier
                .size((160 * breathScale).dp)
                .clip(CircleShape)
                .background(
                    if (isRunning) phaseColors[phaseIndex].copy(alpha = 0.15f)
                    else CoralPrimary.copy(alpha = 0.1f)
                )
                .border(
                    2.dp,
                    if (isRunning) phaseColors[phaseIndex] else CoralPrimary.copy(alpha = 0.4f),
                    CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                if (isRunning) {
                    Text(
                        text = phases[phaseIndex],
                        color = phaseColors[phaseIndex],
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "$countdown",
                        color = TextPrimary,
                        fontSize = 36.sp,
                        fontWeight = FontWeight.Bold
                    )
                } else {
                    Text(
                        text = "Ready",
                        color = CoralPrimary,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (isRunning) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                phases.forEachIndexed { index, phase ->
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(
                                    if (index == phaseIndex) phaseColors[index]
                                    else phaseColors[index].copy(alpha = 0.3f)
                                )
                        )
                        Text(
                            text = phase,
                            color = if (index == phaseIndex) phaseColors[index] else TextSecondary.copy(alpha = 0.5f),
                            fontSize = 11.sp
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Cycles completed: $cycleCount",
                color = TextSecondary,
                fontSize = 13.sp
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                if (isRunning) {
                    isRunning = false
                    cycleCount = 0
                } else {
                    isRunning = true
                    phaseIndex = 0
                    countdown = 4
                    cycleCount = 0
                }
            },
            colors = ButtonDefaults.buttonColors(
                containerColor = if (isRunning) Color(0xFF444444) else CoralPrimary,
                contentColor = Color.White
            ),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text(if (isRunning) "Stop" else "Start Breathing")
        }
    }
}

@Composable
private fun ButterflyHugSection() {
    val steps = remember {
        listOf(
            "Cross your arms over your chest so your fingertips rest just below your collarbones.",
            "Close your eyes or soften your gaze downward.",
            "Alternately tap your hands on your chest, left then right, at a slow, steady pace.",
            "Focus on a calm or safe place while you tap. Notice what you see, hear, smell, and feel.",
            "Continue for 1-2 minutes, or until you feel your body begin to settle.",
            "When you are ready, take a deep breath, open your eyes, and notice how you feel."
        )
    }

    Column {
        Text(
            text = "Butterfly Hug (BLS)",
            color = CoralPrimary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "A bilateral stimulation technique that can help self-soothe during distress.",
            color = TextSecondary,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        Spacer(modifier = Modifier.height(12.dp))

        steps.forEachIndexed { index, step ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(AccentAmber.copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "${index + 1}",
                            color = AccentAmber,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = step,
                        color = TextPrimary,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

@Composable
private fun BodyScanSection() {
    val steps = remember {
        listOf(
            "Find a comfortable position, either sitting or lying down. Close your eyes gently.",
            "Begin by noticing your feet. Are they tense or relaxed? Warm or cool? Simply observe without judgment.",
            "Slowly move your attention upward through your lower legs, knees, and thighs. Notice any tension or sensation.",
            "Bring awareness to your hips, pelvis, and lower back. Breathe into any tightness you notice.",
            "Notice your abdomen rising and falling with each breath. Let your belly soften.",
            "Move attention to your chest, upper back, and shoulders. Allow them to drop away from your ears.",
            "Scan your arms, from shoulders down to your fingertips. Let your hands rest open and relaxed.",
            "Notice your neck, jaw, mouth, and face. Unclench your jaw. Soften the space between your eyebrows.",
            "Finally, notice the top of your head. Imagine warm, healing energy flowing from the crown down through your whole body.",
            "Take three deep breaths. When you are ready, gently open your eyes and return to the present moment."
        )
    }

    Column {
        Text(
            text = "Body Scan Meditation",
            color = CoralPrimary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "A mindfulness exercise to release tension stored in the body. Take about 5-10 minutes.",
            color = TextSecondary,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        Spacer(modifier = Modifier.height(12.dp))

        steps.forEachIndexed { index, step ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF42A5F5).copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "${index + 1}",
                            color = Color(0xFF42A5F5),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = step,
                        color = TextPrimary,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 3 — SAFETY PLAN
// ═══════════════════════════════════════════════════════════════════════════════

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SafetyPlanTab() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val safetyPlanSteps = remember {
        listOf(
            SafetyPlanStep(
                1,
                "Warning Signs",
                "What thoughts, images, moods, situations, or behaviors indicate a crisis may be developing?",
                listOf("Feeling hopeless", "Withdrawing from others", "Increased irritability", "Difficulty sleeping", "Racing thoughts")
            ),
            SafetyPlanStep(
                2,
                "Internal Coping Strategies",
                "What can I do on my own to take my mind off my problems without contacting another person?",
                listOf("Deep breathing", "Going for a walk", "Listening to music", "Journaling", "Exercise", "Meditation")
            ),
            SafetyPlanStep(
                3,
                "People & Social Settings That Provide Distraction",
                "Who or what social settings help me take my mind off my problems?",
                listOf("A trusted friend", "Coffee shop", "Library", "Community center", "Online support group")
            ),
            SafetyPlanStep(
                4,
                "People I Can Ask for Help",
                "Who are people I can reach out to when I am in crisis?",
                listOf("Family member", "Close friend", "Therapist", "Mentor", "Spiritual leader")
            ),
            SafetyPlanStep(
                5,
                "Professionals & Agencies to Contact",
                "Which mental health professionals or agencies can I contact during a crisis?",
                listOf("Therapist", "Psychiatrist", "Vandrevala Foundation", "iCall (TISS)", "Local ER")
            ),
            SafetyPlanStep(
                6,
                "Making the Environment Safe",
                "What can I do to make my environment safer? What items should I remove or secure?",
                listOf("Remove sharp objects", "Lock up medications", "Ask someone to hold items", "Stay in a safe place")
            )
        )
    }

    var stepValues by remember {
        mutableStateOf(List(6) { "" })
    }
    var expandedStep by remember { mutableIntStateOf(-1) }

    // Load saved data from SharedPreferences
    LaunchedEffect(Unit) {
        val prefs = context.getSharedPreferences("trauma_first_aid", Context.MODE_PRIVATE)
        stepValues = List(6) { index ->
            prefs.getString("safety_plan_step_${index + 1}", "") ?: ""
        }
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1520))
            ) {
                Row(modifier = Modifier.padding(14.dp)) {
                    Icon(
                        Icons.Filled.Warning,
                        contentDescription = null,
                        tint = AccentAmber,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "This safety plan is based on the Stanley-Brown model. It is a personal tool to help you during difficult moments. It is not a substitute for professional care. Please work with a clinician to develop a comprehensive safety plan.",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        lineHeight = 17.sp
                    )
                }
            }
        }

        itemsIndexed(safetyPlanSteps) { index, step ->
            val isExpanded = expandedStep == index

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(
                        1.dp,
                        if (isExpanded) CoralPrimary.copy(alpha = 0.5f) else CardBorder,
                        RoundedCornerShape(16.dp)
                    )
                    .clickable { expandedStep = if (isExpanded) -1 else index },
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(CoralPrimary.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "${step.stepNumber}",
                                color = CoralPrimary,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = step.title,
                            color = TextPrimary,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f)
                        )
                        Icon(
                            imageVector = if (isExpanded) Icons.Filled.Close else Icons.Filled.MenuBook,
                            contentDescription = if (isExpanded) "Collapse" else "Expand",
                            tint = TextSecondary.copy(alpha = 0.6f),
                            modifier = Modifier.size(20.dp)
                        )
                    }

                    AnimatedVisibility(
                        visible = isExpanded,
                        enter = expandVertically(animationSpec = tween(300)),
                        exit = shrinkVertically(animationSpec = tween(300))
                    ) {
                        Column {
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = step.prompt,
                                color = TextSecondary,
                                fontSize = 13.sp,
                                lineHeight = 18.sp
                            )
                            Spacer(modifier = Modifier.height(10.dp))

                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                step.examples.forEach { example ->
                                    AssistChip(
                                        onClick = {
                                            val current = stepValues[index]
                                            val newVal = if (current.isBlank()) example
                                            else "$current, $example"
                                            stepValues = stepValues.toMutableList().also { it[index] = newVal }
                                        },
                                        label = { Text(example, fontSize = 11.sp) },
                                        colors = AssistChipDefaults.assistChipColors(
                                            containerColor = AccentAmber.copy(alpha = 0.1f),
                                            labelColor = AccentAmber
                                        ),
                                        border = AssistChipDefaults.assistChipBorder(
                                            borderColor = AccentAmber.copy(alpha = 0.3f),
                                            enabled = true
                                        )
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            OutlinedTextField(
                                value = stepValues[index],
                                onValueChange = { newValue ->
                                    stepValues = stepValues.toMutableList().also { it[index] = newValue }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                placeholder = {
                                    Text(
                                        "Write your personal response here...",
                                        color = TextSecondary.copy(alpha = 0.5f),
                                        fontSize = 13.sp
                                    )
                                },
                                minLines = 3,
                                maxLines = 6,
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedTextColor = TextPrimary,
                                    unfocusedTextColor = TextPrimary,
                                    cursorColor = CoralPrimary,
                                    focusedBorderColor = CoralPrimary,
                                    unfocusedBorderColor = CardBorder,
                                    focusedContainerColor = BackgroundDark,
                                    unfocusedContainerColor = BackgroundDark
                                ),
                                shape = RoundedCornerShape(12.dp)
                            )
                        }
                    }
                }
            }
        }

        item {
            Spacer(modifier = Modifier.height(8.dp))
            Button(
                onClick = {
                    scope.launch {
                        val prefs = context.getSharedPreferences("trauma_first_aid", Context.MODE_PRIVATE)
                        prefs.edit().apply {
                            stepValues.forEachIndexed { index, value ->
                                putString("safety_plan_step_${index + 1}", value)
                            }
                            apply()
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = CoralPrimary,
                    contentColor = Color.White
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(
                    Icons.Filled.SaveAlt,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Save Plan", fontWeight = FontWeight.Bold)
            }
        }

        item { Spacer(modifier = Modifier.height(32.dp)) }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 4 — DE-ESCALATION
// ═══════════════════════════════════════════════════════════════════════════════

@Composable
private fun DeEscalationTab() {
    val context = LocalContext.current

    val leapSteps = remember {
        listOf(
            LeapStep("L", "Listen", "Give the person your full, undivided attention. Reflect back what they say without judgment. Use phrases like \"It sounds like...\" and \"I hear you saying...\". Resist the urge to interrupt or fix. Silence is okay."),
            LeapStep("E", "Empathize", "Acknowledge their feelings and validate their experience. You don't have to agree with their perspective to validate their pain. Say things like \"That sounds really difficult\" or \"I can see why you'd feel that way.\""),
            LeapStep("A", "Agree", "Find common ground wherever possible. Even small agreements build trust. You might agree on a shared goal: \"We both want you to feel safe.\" Agreeing doesn't mean condoning harmful behavior."),
            LeapStep("P", "Partner", "Collaborate on next steps rather than dictating a solution. Ask \"What do you think would help right now?\" or \"How can we work through this together?\" Offer choices to restore their sense of control.")
        )
    }

    val dosList = remember {
        listOf(
            "Stay calm and speak in a low, steady voice",
            "Maintain a non-threatening body posture (open hands, relaxed shoulders)",
            "Give the person physical space and respect boundaries",
            "Acknowledge their feelings without judgment",
            "Use their name if you know it",
            "Ask simple, open-ended questions",
            "Offer choices to restore a sense of control",
            "Set gentle, clear limits if needed"
        )
    }

    val dontsList = remember {
        listOf(
            "Argue, debate, or try to prove them wrong",
            "Raise your voice or match their intensity",
            "Make sudden movements or invade personal space",
            "Touch the person without explicit permission",
            "Use dismissive phrases like \"calm down\" or \"you're overreacting\"",
            "Threaten or issue ultimatums",
            "Take aggressive behavior personally",
            "Leave a suicidal person alone"
        )
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Text(
                text = "LEAP Method",
                color = CoralPrimary,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Developed by Dr. Xavier Amador, the LEAP method is an evidence-based approach for communicating with someone in crisis.",
                color = TextSecondary,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )
        }

        items(leapSteps) { step ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CoralPrimary.copy(alpha = 0.3f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(CoralPrimary.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = step.letter,
                            color = CoralPrimary,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = step.name,
                            color = AccentAmber,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = step.description,
                            color = TextPrimary,
                            fontSize = 13.sp,
                            lineHeight = 19.sp
                        )
                    }
                }
            }
        }

        // Do's section
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Do's",
                color = Color(0xFF66BB6A),
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
        }

        items(dosList) { item ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.Top
            ) {
                Icon(
                    Icons.Filled.Check,
                    contentDescription = null,
                    tint = Color(0xFF66BB6A),
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = item,
                    color = TextPrimary,
                    fontSize = 14.sp,
                    lineHeight = 20.sp
                )
            }
        }

        // Don'ts section
        item {
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "Don'ts",
                color = Color(0xFFEF5350),
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
        }

        items(dontsList) { item ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.Top
            ) {
                Icon(
                    Icons.Filled.Close,
                    contentDescription = null,
                    tint = Color(0xFFEF5350),
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = item,
                    color = TextPrimary,
                    fontSize = 14.sp,
                    lineHeight = 20.sp
                )
            }
        }

        // When to call 112
        item {
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFFF1744), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF2A0A0A))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Filled.Warning,
                            contentDescription = null,
                            tint = Color(0xFFFF1744),
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "When to Call 112",
                            color = Color(0xFFFF1744),
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(10.dp))

                    val emergencySigns = listOf(
                        "The person has a weapon or access to lethal means",
                        "There is an active threat of violence to self or others",
                        "The person is experiencing a medical emergency (overdose, self-harm with injury)",
                        "The person is severely disoriented or psychotic and at risk of harm",
                        "You feel unsafe or unable to manage the situation"
                    )

                    emergencySigns.forEach { sign ->
                        Row(
                            modifier = Modifier.padding(vertical = 3.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Text(
                                text = "\u2022",
                                color = Color(0xFFFF1744),
                                fontSize = 14.sp
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = sign,
                                color = TextPrimary,
                                fontSize = 13.sp,
                                lineHeight = 18.sp
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Button(
                        onClick = {
                            val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:112"))
                            context.startActivity(dialIntent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFFFF1744),
                            contentColor = Color.White
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(
                            Icons.Filled.Phone,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Call 112", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(32.dp)) }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 5 — LEARN
// ═══════════════════════════════════════════════════════════════════════════════

@Composable
private fun LearnTab() {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Common Trauma Responses
        item { LearnSectionHeader("Common Trauma Responses") }

        item {
            val responseCategories = listOf(
                Triple("Emotional", Color(0xFFEF5350), listOf(
                    "Intense fear, anxiety, or panic",
                    "Sadness, grief, or depression",
                    "Anger, irritability, or mood swings",
                    "Guilt, shame, or self-blame",
                    "Emotional numbness or detachment",
                    "Feeling overwhelmed or helpless"
                )),
                Triple("Physical", Color(0xFFFFA726), listOf(
                    "Rapid heartbeat or palpitations",
                    "Muscle tension or chronic pain",
                    "Fatigue or exhaustion",
                    "Difficulty sleeping or nightmares",
                    "Startled easily (hypervigilance)",
                    "Nausea or digestive issues"
                )),
                Triple("Cognitive", Color(0xFF42A5F5), listOf(
                    "Intrusive memories or flashbacks",
                    "Difficulty concentrating or making decisions",
                    "Memory gaps related to the event",
                    "Confusion or disorientation",
                    "Negative beliefs about self or world",
                    "Dissociation or feeling unreal"
                )),
                Triple("Behavioral", Color(0xFF66BB6A), listOf(
                    "Avoidance of reminders of the event",
                    "Social withdrawal or isolation",
                    "Changes in eating or sleeping patterns",
                    "Increased use of alcohol or substances",
                    "Difficulty maintaining routines",
                    "Risk-taking or self-destructive behavior"
                ))
            )

            responseCategories.forEach { (category, color, responses) ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 10.dp)
                        .border(1.dp, color.copy(alpha = 0.3f), RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceDark)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = category,
                            color = color,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        responses.forEach { response ->
                            Row(
                                modifier = Modifier.padding(vertical = 2.dp),
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    text = "\u2022",
                                    color = color.copy(alpha = 0.7f),
                                    fontSize = 14.sp
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = response,
                                    color = TextPrimary,
                                    fontSize = 13.sp,
                                    lineHeight = 18.sp
                                )
                            }
                        }
                    }
                }
            }
        }

        // Trauma-Informed Care Principles
        item { LearnSectionHeader("6 Principles of Trauma-Informed Care") }

        item {
            val principles = listOf(
                "Safety" to "Throughout the organization, staff and the people they serve feel physically and psychologically safe. The physical setting is safe and interpersonal interactions promote a sense of safety.",
                "Trustworthiness & Transparency" to "Organizational operations and decisions are conducted with transparency. The goal is building and maintaining trust with clients, family members, and among staff.",
                "Peer Support" to "Mutual self-help and peer support are key vehicles for establishing safety and hope, building trust, enhancing collaboration, and sharing recovery stories.",
                "Collaboration & Mutuality" to "There is recognition that healing happens in relationships and in the meaningful sharing of power and decision-making. Everyone has a role to play.",
                "Empowerment, Voice & Choice" to "Individual strengths and experiences are recognized and built upon. Organizations foster a belief in resilience and the ability of individuals to heal and promote recovery.",
                "Cultural, Historical & Gender Issues" to "The organization actively moves past cultural stereotypes and biases, offers culturally responsive services, and recognizes and addresses historical trauma."
            )

            principles.forEach { (name, description) ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp)
                        .border(1.dp, AccentAmber.copy(alpha = 0.25f), RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceDark)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = name,
                            color = AccentAmber,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = description,
                            color = TextPrimary,
                            fontSize = 13.sp,
                            lineHeight = 18.sp
                        )
                    }
                }
            }
        }

        // When to Seek Help
        item { LearnSectionHeader("When to Seek Professional Help") }

        item {
            val warningSigns = listOf(
                "Symptoms persist for more than a month after the event",
                "You are unable to carry out daily activities or work",
                "You are having thoughts of harming yourself or others",
                "You are using alcohol or drugs to cope",
                "Relationships are significantly affected",
                "You feel persistently numb or disconnected from others",
                "You experience frequent nightmares or flashbacks",
                "You avoid anything that reminds you of the trauma",
                "You feel constantly on edge, fearful, or anxious",
                "You notice significant changes in appetite or weight"
            )

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CoralPrimary.copy(alpha = 0.3f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    warningSigns.forEach { sign ->
                        Row(
                            modifier = Modifier.padding(vertical = 3.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Icon(
                                Icons.Filled.Warning,
                                contentDescription = null,
                                tint = CoralPrimary.copy(alpha = 0.7f),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = sign,
                                color = TextPrimary,
                                fontSize = 13.sp,
                                lineHeight = 18.sp
                            )
                        }
                    }
                }
            }
        }

        // Harmful Practices
        item { LearnSectionHeader("Harmful Practices to Avoid") }

        item {
            val harmfulPractices = listOf(
                "Forced debriefing" to "Mandatory psychological debriefing immediately after a traumatic event can actually worsen outcomes. Individuals should not be forced to talk about what happened before they are ready.",
                "Minimizing or dismissing" to "Telling someone to \"get over it\" or that \"it wasn't that bad\" invalidates their experience and can increase shame and isolation.",
                "Pathologizing normal responses" to "Treating normal stress reactions as symptoms of mental illness can be harmful. Most trauma responses are normal reactions to abnormal events.",
                "Forcing forgiveness" to "Pressuring someone to forgive their abuser or the source of their trauma before they are ready can retraumatize them and undermine their healing process.",
                "Unsolicited advice" to "Offering solutions or telling someone what they \"should\" do without being asked can feel controlling and dismissive of their autonomy."
            )

            harmfulPractices.forEach { (practice, explanation) ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp)
                        .border(1.dp, Color(0xFFEF5350).copy(alpha = 0.25f), RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceDark)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Filled.Close,
                                contentDescription = null,
                                tint = Color(0xFFEF5350),
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = practice,
                                color = Color(0xFFEF5350),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = explanation,
                            color = TextPrimary,
                            fontSize = 13.sp,
                            lineHeight = 18.sp
                        )
                    }
                }
            }
        }

        // PFA Overview
        item { LearnSectionHeader("Psychological First Aid (PFA) Overview") }

        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFF42A5F5).copy(alpha = 0.3f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "WHO Look-Listen-Link Framework",
                        color = Color(0xFF42A5F5),
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val whoSteps = listOf(
                        "Look" to "Check for safety, check for people with obvious urgent basic needs, and check for people with serious distress reactions.",
                        "Listen" to "Approach people who may need support, ask about their needs and concerns, listen actively, and help them feel calm.",
                        "Link" to "Help people address basic needs, access services, cope with problems, give information, and connect people with loved ones and social support."
                    )

                    whoSteps.forEach { (step, description) ->
                        Row(
                            modifier = Modifier.padding(vertical = 4.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(28.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF42A5F5).copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = step.first().toString(),
                                    color = Color(0xFF42A5F5),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = step,
                                    color = Color(0xFF42A5F5),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Text(
                                    text = description,
                                    color = TextPrimary,
                                    fontSize = 13.sp,
                                    lineHeight = 18.sp
                                )
                            }
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(4.dp)) }

        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFF66BB6A).copy(alpha = 0.3f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceDark)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "5-Step PFA Model",
                        color = Color(0xFF66BB6A),
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val pfaSteps = listOf(
                        "1. Promote Safety" to "Help the person feel physically and emotionally safe. Remove them from danger if possible and provide a calm environment.",
                        "2. Promote Calm" to "Use grounding techniques, validate their feelings, and provide clear, honest information to reduce uncertainty.",
                        "3. Promote Self-Efficacy" to "Empower the person by helping them identify their own strengths, coping skills, and resources.",
                        "4. Promote Connectedness" to "Help the person connect with loved ones, community resources, and support systems.",
                        "5. Promote Hope" to "Normalize their reactions, express confidence in their ability to cope, and share that recovery is possible with time and support."
                    )

                    pfaSteps.forEach { (step, description) ->
                        Row(
                            modifier = Modifier.padding(vertical = 4.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Text(
                                text = "\u2022",
                                color = Color(0xFF66BB6A),
                                fontSize = 14.sp
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = step,
                                    color = Color(0xFF66BB6A),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Text(
                                    text = description,
                                    color = TextPrimary,
                                    fontSize = 13.sp,
                                    lineHeight = 18.sp
                                )
                            }
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(32.dp)) }
    }
}

@Composable
private fun LearnSectionHeader(title: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp, bottom = 4.dp)
    ) {
        Text(
            text = title,
            color = CoralPrimary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(6.dp))
        HorizontalDivider(
            color = CoralPrimary.copy(alpha = 0.3f),
            thickness = 1.dp
        )
    }
}
