package com.teloscopy.app.ui.screens

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
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
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.teloscopy.app.ui.theme.Background
import com.teloscopy.app.ui.theme.OnBackground
import com.teloscopy.app.ui.theme.OnSurfaceVariant
import com.teloscopy.app.ui.theme.Primary
import com.teloscopy.app.ui.theme.Secondary
import com.teloscopy.app.ui.theme.Surface
import com.teloscopy.app.ui.theme.Tertiary
import com.teloscopy.app.viewmodel.ChatMessage
import com.teloscopy.app.viewmodel.PsychiatryUiState
import com.teloscopy.app.viewmodel.PsychiatryViewModel
import kotlinx.coroutines.launch
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun PsychiatryScreen(
    viewModel: PsychiatryViewModel,
    onBack: () -> Unit,
    onCrisisDetected: (String) -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val currentTheme by viewModel.currentTheme.collectAsState()
    val themes by viewModel.themes.collectAsState()
    val crisisAlert by viewModel.crisisAlert.collectAsState()

    LaunchedEffect(crisisAlert) {
        crisisAlert?.let { crisis ->
            onCrisisDetected(crisis.severity)
            viewModel.clearCrisisAlert()
        }
    }

    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }

    // TTS
    val context = LocalContext.current
    var tts by remember { mutableStateOf<TextToSpeech?>(null) }
    var ttsReady by remember { mutableStateOf(false) }

    // STT (Speech-to-Text)
    var isListening by remember { mutableStateOf(false) }
    var hasMicPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED
        )
    }
    val speechAvailable = remember { SpeechRecognizer.isRecognitionAvailable(context) }
    var speechRecognizer by remember { mutableStateOf<SpeechRecognizer?>(null) }

    val micPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasMicPermission = granted
        if (!granted) {
            scope.launch {
                snackbarHostState.showSnackbar("Microphone permission is required for voice input")
            }
        }
    }

    // Create SpeechRecognizer
    DisposableEffect(Unit) {
        if (speechAvailable) {
            val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
            recognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) { isListening = true }
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() { isListening = false }
                override fun onError(error: Int) {
                    isListening = false
                    if (error != SpeechRecognizer.ERROR_NO_MATCH &&
                        error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                        val msg = when (error) {
                            SpeechRecognizer.ERROR_NETWORK -> "Network error — check connection"
                            SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission denied"
                            else -> "Voice recognition error ($error)"
                        }
                        scope.launch { snackbarHostState.showSnackbar(msg) }
                    }
                }
                override fun onResults(results: Bundle?) {
                    isListening = false
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!matches.isNullOrEmpty()) {
                        val spoken = matches[0]
                        inputText = if (inputText.isBlank()) spoken
                            else "$inputText $spoken"
                    }
                }
                override fun onPartialResults(partialResults: Bundle?) {
                    val partial = partialResults
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!partial.isNullOrEmpty()) {
                        // Show partial transcription as placeholder hint
                    }
                }
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            speechRecognizer = recognizer
        }
        onDispose {
            speechRecognizer?.destroy()
        }
    }

    fun startListening() {
        if (!hasMicPermission) {
            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            return
        }
        if (!speechAvailable) {
            scope.launch {
                snackbarHostState.showSnackbar("Speech recognition not available on this device")
            }
            return
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-IN")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }
        speechRecognizer?.startListening(intent)
    }

    fun stopListening() {
        speechRecognizer?.stopListening()
        isListening = false
    }

    DisposableEffect(Unit) {
        val engine = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                ttsReady = true
            }
        }
        tts = engine
        onDispose {
            engine.stop()
            engine.shutdown()
        }
    }

    // Configure TTS when ready
    LaunchedEffect(ttsReady) {
        if (ttsReady) {
            tts?.let { engine ->
                engine.language = Locale.UK
                engine.setSpeechRate(0.88f)
                engine.setPitch(0.95f)
            }
        }
    }

    // Auto-scroll to bottom
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    // Error handling
    LaunchedEffect(uiState) {
        if (uiState is PsychiatryUiState.Error) {
            snackbarHostState.showSnackbar(
                (uiState as PsychiatryUiState.Error).message
            )
            viewModel.clearError()
        }
    }

    fun speakText(text: String) {
        if (!ttsReady || tts == null) return
        tts?.stop()
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "counsel_${System.currentTimeMillis()}")
    }

    Scaffold(
        containerColor = Background,
        snackbarHost = {
            SnackbarHost(snackbarHostState) { data ->
                Snackbar(
                    snackbarData = data,
                    containerColor = Color(0xFF442222),
                    contentColor = Color.White
                )
            }
        },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            "Counselling",
                            color = OnBackground,
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp
                        )
                        if (currentTheme.isNotEmpty()) {
                            val title = themes[currentTheme]?.title ?: currentTheme
                            Text(
                                title,
                                color = Tertiary,
                                fontSize = 12.sp
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = OnBackground
                        )
                    }
                },
                actions = {
                    if (messages.isNotEmpty()) {
                        IconButton(onClick = {
                            tts?.stop()
                            viewModel.clearChat()
                        }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = "Clear chat",
                                tint = OnSurfaceVariant
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Surface
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding()
        ) {
            // Chat messages
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                state = listState,
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Welcome message if empty
                if (messages.isEmpty()) {
                    item {
                        WelcomeCard()
                    }
                }

                items(messages, key = { "${it.role}_${it.text.hashCode()}_${messages.indexOf(it)}" }) { msg ->
                    AnimatedVisibility(
                        visible = true,
                        enter = fadeIn() + slideInVertically { it / 2 }
                    ) {
                        ChatBubble(
                            message = msg,
                            onSpeak = { speakText(msg.text) },
                            onFollowup = { text ->
                                inputText = ""
                                viewModel.sendMessage(text)
                            },
                            ttsReady = ttsReady
                        )
                    }
                }

                // Typing indicator
                if (uiState is PsychiatryUiState.Sending) {
                    item {
                        TypingIndicator()
                    }
                }
            }

            // Input bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Surface)
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Microphone button
                IconButton(
                    onClick = {
                        if (isListening) stopListening() else startListening()
                    },
                    enabled = uiState !is PsychiatryUiState.Sending,
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(
                            if (isListening) Color(0xFFE53935)
                            else Secondary.copy(alpha = 0.15f)
                        )
                ) {
                    Icon(
                        if (isListening) Icons.Default.MicOff else Icons.Default.Mic,
                        contentDescription = if (isListening) "Stop listening" else "Voice input",
                        tint = if (isListening) Color.White else Primary,
                        modifier = Modifier.size(20.dp)
                    )
                }

                Spacer(modifier = Modifier.width(8.dp))

                OutlinedTextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    modifier = Modifier.weight(1f),
                    placeholder = {
                        Text(
                            if (isListening) "Listening\u2026"
                            else "Share what's on your mind\u2026",
                            color = if (isListening) Color(0xFFE53935).copy(alpha = 0.8f)
                            else OnSurfaceVariant.copy(alpha = 0.6f)
                        )
                    },
                    maxLines = 4,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = OnBackground,
                        unfocusedTextColor = OnBackground,
                        cursorColor = Primary,
                        focusedBorderColor = Primary,
                        unfocusedBorderColor = OnSurfaceVariant.copy(alpha = 0.3f),
                        focusedContainerColor = Background,
                        unfocusedContainerColor = Background
                    ),
                    shape = RoundedCornerShape(20.dp),
                    enabled = uiState !is PsychiatryUiState.Sending
                )

                Spacer(modifier = Modifier.width(8.dp))

                IconButton(
                    onClick = {
                        if (inputText.isNotBlank()) {
                            if (isListening) stopListening()
                            val text = inputText
                            inputText = ""
                            viewModel.sendMessage(text)
                        }
                    },
                    enabled = inputText.isNotBlank() && uiState !is PsychiatryUiState.Sending,
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(
                            if (inputText.isNotBlank()) Primary else Primary.copy(alpha = 0.3f)
                        )
                ) {
                    if (uiState is PsychiatryUiState.Sending) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Icon(
                            Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Send",
                            tint = Color.White,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun WelcomeCard() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 32.dp, horizontal = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(
                    Brush.linearGradient(
                        colors = listOf(Primary, Tertiary)
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text("\uD83E\uDDE0", fontSize = 32.sp)
        }
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            "Reflective Counselling",
            color = OnBackground,
            fontWeight = FontWeight.Bold,
            fontSize = 22.sp
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "A safe space for self-reflection through inquiry-based dialogue.\nThis is not a substitute for professional therapy.",
            color = OnSurfaceVariant,
            fontSize = 14.sp,
            textAlign = TextAlign.Center,
            lineHeight = 20.sp
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            "Try saying: \"I've been feeling overwhelmed lately\"",
            color = Primary.copy(alpha = 0.8f),
            fontSize = 13.sp,
            fontStyle = FontStyle.Italic,
            textAlign = TextAlign.Center
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ChatBubble(
    message: ChatMessage,
    onSpeak: () -> Unit,
    onFollowup: (String) -> Unit,
    ttsReady: Boolean
) {
    val isUser = message.role == "user"

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (isUser) 16.dp else 4.dp,
                        bottomEnd = if (isUser) 4.dp else 16.dp
                    )
                )
                .background(
                    if (isUser) Primary.copy(alpha = 0.15f)
                    else Surface
                )
                .padding(12.dp)
        ) {
            Column {
                if (!isUser) {
                    Text(
                        "Counsellor",
                        color = Tertiary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Text(
                    message.text,
                    color = OnBackground,
                    fontSize = 15.sp,
                    lineHeight = 22.sp
                )

                // Speak button for counsellor messages
                if (!isUser && ttsReady) {
                    Spacer(modifier = Modifier.height(6.dp))
                    IconButton(
                        onClick = onSpeak,
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            Icons.Default.VolumeUp,
                            contentDescription = "Listen",
                            tint = OnSurfaceVariant.copy(alpha = 0.6f),
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
        }

        // Follow-up chips
        if (!isUser && message.followups.isNotEmpty()) {
            Spacer(modifier = Modifier.height(6.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                message.followups.forEach { followup ->
                    AssistChip(
                        onClick = { onFollowup(followup) },
                        label = {
                            Text(
                                followup,
                                fontSize = 12.sp,
                                maxLines = 2
                            )
                        },
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = Primary.copy(alpha = 0.1f),
                            labelColor = Primary
                        ),
                        border = AssistChipDefaults.assistChipBorder(
                            borderColor = Primary.copy(alpha = 0.3f),
                            enabled = true
                        )
                    )
                }
            }
        }
    }
}

@Composable
private fun TypingIndicator() {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Surface)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            "Counsellor",
            color = Tertiary,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold
        )
        Spacer(modifier = Modifier.width(8.dp))
        CircularProgressIndicator(
            modifier = Modifier.size(14.dp),
            color = Tertiary,
            strokeWidth = 2.dp
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            "Reflecting\u2026",
            color = OnSurfaceVariant,
            fontSize = 13.sp,
            fontStyle = FontStyle.Italic
        )
    }
}
