package com.teloscopy.app.viewmodel

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.teloscopy.app.data.api.HealthCheckupResponse
import com.teloscopy.app.data.api.ReportParsePreview
import com.teloscopy.app.data.api.TeloscopyApi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject

/** Possible states for the health checkup screen. */
enum class CheckupState {
    IDLE,
    PARSING,
    PARSED,
    ANALYZING,
    RESULTS,
    ERROR
}

@HiltViewModel
class HealthCheckupViewModel @Inject constructor(
    private val api: TeloscopyApi
) : ViewModel() {

    private val _state = MutableStateFlow(CheckupState.IDLE)
    val state: StateFlow<CheckupState> = _state.asStateFlow()

    private val _parsePreview = MutableStateFlow<ReportParsePreview?>(null)
    val parsePreview: StateFlow<ReportParsePreview?> = _parsePreview.asStateFlow()

    private val _checkupResponse = MutableStateFlow<HealthCheckupResponse?>(null)
    val checkupResponse: StateFlow<HealthCheckupResponse?> = _checkupResponse.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    /** Tracks the selected file URI (set from the UI). */
    private val _selectedFileUri = MutableStateFlow<Uri?>(null)
    val selectedFileUri: StateFlow<Uri?> = _selectedFileUri.asStateFlow()

    private val _selectedFileName = MutableStateFlow("")
    val selectedFileName: StateFlow<String> = _selectedFileName.asStateFlow()

    // Profile fields
    var age: String = ""
    var sex: String = "male"
    var region: String = "South Indian"

    fun setFile(uri: Uri?, name: String) {
        _selectedFileUri.value = uri
        _selectedFileName.value = name
        _state.value = CheckupState.IDLE
        _parsePreview.value = null
        _checkupResponse.value = null
        _errorMessage.value = null
    }

    fun clearFile() {
        _selectedFileUri.value = null
        _selectedFileName.value = ""
        _parsePreview.value = null
        _checkupResponse.value = null
        _state.value = CheckupState.IDLE
        _errorMessage.value = null
    }

    /**
     * Parse report: upload file to /api/health-checkup/parse-report
     * for a preview of extracted values.
     */
    fun parseReport(fileBytes: ByteArray, fileName: String) {
        viewModelScope.launch {
            _state.value = CheckupState.PARSING
            _errorMessage.value = null
            try {
                val mediaType = guessMediaType(fileName)
                val requestBody = fileBytes.toRequestBody(mediaType.toMediaType())
                val part = MultipartBody.Part.createFormData("file", fileName, requestBody)
                val preview = api.parseHealthReport(part)
                _parsePreview.value = preview
                _state.value = CheckupState.PARSED
            } catch (e: Exception) {
                _errorMessage.value = e.message ?: "Failed to parse report"
                _state.value = CheckupState.ERROR
            }
        }
    }

    /**
     * Upload report + profile and get full analysis.
     */
    fun uploadAndAnalyze(fileBytes: ByteArray, fileName: String) {
        viewModelScope.launch {
            _state.value = CheckupState.ANALYZING
            _errorMessage.value = null
            try {
                val mediaType = guessMediaType(fileName)
                val requestBody = fileBytes.toRequestBody(mediaType.toMediaType())
                val part = MultipartBody.Part.createFormData("file", fileName, requestBody)

                val response = api.uploadHealthReport(
                    file = part,
                    age = age.toRequestBody("text/plain".toMediaType()),
                    sex = sex.toRequestBody("text/plain".toMediaType()),
                    region = region.toRequestBody("text/plain".toMediaType()),
                    country = null,
                    state = null,
                    dietaryRestrictions = null,
                    knownVariants = null,
                    calorieTarget = "2000".toRequestBody("text/plain".toMediaType()),
                    mealPlanDays = "7".toRequestBody("text/plain".toMediaType()),
                    healthConditions = null
                )
                _checkupResponse.value = response
                _state.value = CheckupState.RESULTS
            } catch (e: Exception) {
                _errorMessage.value = e.message ?: "Analysis failed"
                _state.value = CheckupState.ERROR
            }
        }
    }

    fun dismissError() {
        _errorMessage.value = null
        if (_state.value == CheckupState.ERROR) {
            _state.value = if (_parsePreview.value != null) CheckupState.PARSED else CheckupState.IDLE
        }
    }

    fun reset() {
        _state.value = CheckupState.IDLE
        _parsePreview.value = null
        _checkupResponse.value = null
        _errorMessage.value = null
        _selectedFileUri.value = null
        _selectedFileName.value = ""
    }

    private fun guessMediaType(name: String): String {
        val lower = name.lowercase()
        return when {
            lower.endsWith(".pdf") -> "application/pdf"
            lower.endsWith(".png") -> "image/png"
            lower.endsWith(".jpg") || lower.endsWith(".jpeg") -> "image/jpeg"
            lower.endsWith(".tif") || lower.endsWith(".tiff") -> "image/tiff"
            lower.endsWith(".bmp") -> "image/bmp"
            lower.endsWith(".webp") -> "image/webp"
            lower.endsWith(".txt") || lower.endsWith(".text") -> "text/plain"
            else -> "application/octet-stream"
        }
    }

    private fun String.toRequestBody(mediaType: okhttp3.MediaType) =
        this.toRequestBody(mediaType)
}
