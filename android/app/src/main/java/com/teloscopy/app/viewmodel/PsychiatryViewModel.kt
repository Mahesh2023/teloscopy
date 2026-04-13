package com.teloscopy.app.viewmodel

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.teloscopy.app.data.api.ConsentPurpose
import com.teloscopy.app.data.api.ConsentTokenRequest
import com.teloscopy.app.data.api.CounselMessage
import com.teloscopy.app.data.api.CounselRequest
import com.teloscopy.app.data.api.CounselResponse
import com.teloscopy.app.data.api.TeloscopyApi
import com.teloscopy.app.data.api.ThemeInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class ChatMessage(
    val role: String,  // "user" or "counsellor" or "system"
    val text: String,
    val followups: List<String> = emptyList()
)

sealed class PsychiatryUiState {
    data object Loading : PsychiatryUiState()
    data object Ready : PsychiatryUiState()
    data object Sending : PsychiatryUiState()
    data class Error(val message: String) : PsychiatryUiState()
}

@HiltViewModel
class PsychiatryViewModel @Inject constructor(
    private val api: TeloscopyApi,
    private val dataStore: DataStore<Preferences>
) : ViewModel() {

    companion object {
        private val CONSENT_TOKEN_KEY = stringPreferencesKey("consent_token")
        private val SESSION_ID_KEY = stringPreferencesKey("session_id")
        private val ALL_PURPOSES = listOf(
            "telomere_analysis", "facial_analysis", "genetic_data",
            "disease_risk", "nutrition_plan", "profile_data",
            "health_report", "psychiatry"
        )
    }

    private val _uiState = MutableStateFlow<PsychiatryUiState>(PsychiatryUiState.Loading)
    val uiState: StateFlow<PsychiatryUiState> = _uiState.asStateFlow()

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _themes = MutableStateFlow<Map<String, ThemeInfo>>(emptyMap())
    val themes: StateFlow<Map<String, ThemeInfo>> = _themes.asStateFlow()

    private val _currentTheme = MutableStateFlow("")
    val currentTheme: StateFlow<String> = _currentTheme.asStateFlow()

    init {
        viewModelScope.launch {
            ensureConsentToken()
            loadThemes()
        }
    }

    private suspend fun getConsentToken(): String? {
        return dataStore.data.map { it[CONSENT_TOKEN_KEY] }.first()
    }

    private suspend fun getOrCreateSessionId(): String {
        val existing = dataStore.data.map { it[SESSION_ID_KEY] }.first()
        if (existing != null) return existing
        val newId = UUID.randomUUID().toString()
        dataStore.edit { it[SESSION_ID_KEY] = newId }
        return newId
    }

    private suspend fun ensureConsentToken() {
        val existing = getConsentToken()
        if (existing != null) return
        try {
            val sessionId = getOrCreateSessionId()
            val request = ConsentTokenRequest(
                sessionId = sessionId,
                agConfirmed = true,
                consents = ALL_PURPOSES.map { ConsentPurpose(purpose = it, granted = true) }
            )
            val response = api.submitConsent(request)
            if (response.isSuccessful) {
                response.body()?.let { body ->
                    dataStore.edit { it[CONSENT_TOKEN_KEY] = body.consentToken }
                }
            }
        } catch (e: Exception) {
            // Will retry on next API call
        }
    }

    private suspend fun refreshConsentToken(): String? {
        try {
            val sessionId = getOrCreateSessionId()
            val request = ConsentTokenRequest(
                sessionId = sessionId,
                agConfirmed = true,
                consents = ALL_PURPOSES.map { ConsentPurpose(purpose = it, granted = true) }
            )
            val response = api.submitConsent(request)
            if (response.isSuccessful) {
                response.body()?.let { body ->
                    dataStore.edit { it[CONSENT_TOKEN_KEY] = body.consentToken }
                    return body.consentToken
                }
            }
        } catch (_: Exception) {}
        return null
    }

    private suspend fun loadThemes() {
        try {
            val token = getConsentToken() ?: refreshConsentToken() ?: run {
                _uiState.value = PsychiatryUiState.Ready
                return
            }
            val response = api.getCounsellingThemes(token)
            if (response.isSuccessful) {
                response.body()?.let { _themes.value = it.themes }
            } else if (response.code() == 403) {
                refreshConsentToken()?.let { newToken ->
                    val retry = api.getCounsellingThemes(newToken)
                    if (retry.isSuccessful) {
                        retry.body()?.let { _themes.value = it.themes }
                    }
                }
            }
        } catch (_: Exception) {}
        _uiState.value = PsychiatryUiState.Ready
    }

    fun sendMessage(text: String) {
        if (text.isBlank()) return
        val userMsg = ChatMessage(role = "user", text = text.trim())
        _messages.value = _messages.value + userMsg
        _uiState.value = PsychiatryUiState.Sending

        viewModelScope.launch {
            try {
                val token = getConsentToken() ?: refreshConsentToken()
                    ?: throw Exception("Could not obtain consent token")

                val conversation = _messages.value.map {
                    CounselMessage(role = it.role, text = it.text)
                }
                val request = CounselRequest(
                    message = text.trim(),
                    conversation = conversation
                )
                val response = api.sendCounselMessage(token, request)

                if (response.isSuccessful) {
                    response.body()?.let { body ->
                        _currentTheme.value = body.theme
                        val counsellorMsg = ChatMessage(
                            role = "counsellor",
                            text = body.displayText,
                            followups = body.followups
                        )
                        _messages.value = _messages.value + counsellorMsg
                    }
                    _uiState.value = PsychiatryUiState.Ready
                } else if (response.code() == 403) {
                    val newToken = refreshConsentToken()
                        ?: throw Exception("Consent expired")
                    val retry = api.sendCounselMessage(newToken, request)
                    if (retry.isSuccessful) {
                        retry.body()?.let { body ->
                            _currentTheme.value = body.theme
                            val counsellorMsg = ChatMessage(
                                role = "counsellor",
                                text = body.displayText,
                                followups = body.followups
                            )
                            _messages.value = _messages.value + counsellorMsg
                        }
                        _uiState.value = PsychiatryUiState.Ready
                    } else {
                        throw Exception("Server error: ${retry.code()}")
                    }
                } else {
                    throw Exception("Server error: ${response.code()}")
                }
            } catch (e: Exception) {
                _uiState.value = PsychiatryUiState.Error(
                    e.message ?: "Something went wrong"
                )
            }
        }
    }

    fun clearError() {
        _uiState.value = PsychiatryUiState.Ready
    }

    fun clearChat() {
        _messages.value = emptyList()
        _currentTheme.value = ""
    }
}
