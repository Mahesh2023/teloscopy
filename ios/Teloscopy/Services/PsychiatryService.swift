// PsychiatryService.swift
// Teloscopy
//
// Handles psychiatry/counselling API communication and consent tokens.

import Foundation

@MainActor
class PsychiatryService: ObservableObject {
    static let shared = PsychiatryService()
    
    @Published var messages: [ChatMessage] = []
    @Published var isLoading = false
    @Published var error: String?
    @Published var themes: [String: ThemeInfo] = [:]
    @Published var currentTheme = ""
    
    private var consentToken: String? {
        get { UserDefaults.standard.string(forKey: "consent_token") }
        set { UserDefaults.standard.set(newValue, forKey: "consent_token") }
    }
    
    private var sessionId: String {
        if let existing = UserDefaults.standard.string(forKey: "session_id") {
            return existing
        }
        let newId = UUID().uuidString
        UserDefaults.standard.set(newId, forKey: "session_id")
        return newId
    }
    
    private let allPurposes = [
        "telomere_analysis", "facial_analysis", "genetic_data",
        "disease_risk", "nutrition_plan", "profile_data",
        "health_report", "psychiatry"
    ]
    
    private var baseURL: String {
        let stored = UserDefaults.standard.string(forKey: "server_url") ?? "http://localhost:8000"
        return stored.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    struct ChatMessage: Identifiable {
        let id = UUID()
        let role: String  // "user" or "counsellor"
        let text: String
        let followups: [String]
        
        init(role: String, text: String, followups: [String] = []) {
            self.role = role
            self.text = text
            self.followups = followups
        }
    }
    
    private init() {
        Task { await ensureConsentToken() }
    }
    
    // MARK: - Consent Token
    
    private func ensureConsentToken() async {
        guard consentToken == nil else { return }
        await refreshConsentToken()
    }
    
    @discardableResult
    private func refreshConsentToken() async -> String? {
        let url = URL(string: "\(baseURL)/api/legal/consent")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("TeloscopyiOS", forHTTPHeaderField: "X-Requested-With")
        
        let body = ConsentTokenRequest(
            sessionId: sessionId,
            dataPrincipalAgeConfirmed: true,
            consents: allPurposes.map { ConsentPurposeItem(purpose: $0, granted: true) }
        )
        
        do {
            request.httpBody = try JSONEncoder().encode(body)
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                return nil
            }
            let decoded = try JSONDecoder().decode(ConsentTokenResponse.self, from: data)
            consentToken = decoded.consentToken
            return decoded.consentToken
        } catch {
            return nil
        }
    }
    
    // MARK: - API Calls
    
    func loadThemes() async {
        guard let token = consentToken ?? (await refreshConsentToken()) else { return }
        
        let url = URL(string: "\(baseURL)/api/psychiatry/themes")!
        var request = URLRequest(url: url)
        request.setValue(token, forHTTPHeaderField: "X-Consent-Token")
        request.setValue("TeloscopyiOS", forHTTPHeaderField: "X-Requested-With")
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else { return }
            
            if http.statusCode == 403 {
                if let newToken = await refreshConsentToken() {
                    var retry = request
                    retry.setValue(newToken, forHTTPHeaderField: "X-Consent-Token")
                    let (retryData, _) = try await URLSession.shared.data(for: retry)
                    let decoded = try JSONDecoder().decode(ThemesResponse.self, from: retryData)
                    themes = decoded.themes
                    return
                }
            }
            
            let decoded = try JSONDecoder().decode(ThemesResponse.self, from: data)
            themes = decoded.themes
        } catch {
            // Themes are optional, don't show error
        }
    }
    
    func sendMessage(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        
        let userMsg = ChatMessage(role: "user", text: trimmed)
        messages.append(userMsg)
        isLoading = true
        error = nil
        
        do {
            guard let token = consentToken ?? (await refreshConsentToken()) else {
                throw NSError(domain: "Teloscopy", code: 403, userInfo: [NSLocalizedDescriptionKey: "Could not obtain consent token"])
            }
            
            let conversation = messages.map { CounselMessage(role: $0.role, text: $0.text) }
            let body = CounselRequest(message: trimmed, conversation: conversation)
            
            let responseBody = try await postCounsel(body: body, token: token)
            
            currentTheme = responseBody.theme
            let counsellorMsg = ChatMessage(
                role: "counsellor",
                text: responseBody.displayText,
                followups: responseBody.followups
            )
            messages.append(counsellorMsg)
            isLoading = false
            
        } catch {
            isLoading = false
            self.error = error.localizedDescription
        }
    }
    
    private func postCounsel(body: CounselRequest, token: String) async throws -> CounselResponse {
        let url = URL(string: "\(baseURL)/api/psychiatry/counsel")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(token, forHTTPHeaderField: "X-Consent-Token")
        request.setValue("TeloscopyiOS", forHTTPHeaderField: "X-Requested-With")
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw NSError(domain: "Teloscopy", code: 0, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
        }
        
        if http.statusCode == 403 {
            if let newToken = await refreshConsentToken() {
                var retry = request
                retry.setValue(newToken, forHTTPHeaderField: "X-Consent-Token")
                let (retryData, retryResp) = try await URLSession.shared.data(for: retry)
                guard let retryHttp = retryResp as? HTTPURLResponse, (200...299).contains(retryHttp.statusCode) else {
                    throw NSError(domain: "Teloscopy", code: 403, userInfo: [NSLocalizedDescriptionKey: "Consent expired"])
                }
                return try JSONDecoder().decode(CounselResponse.self, from: retryData)
            }
            throw NSError(domain: "Teloscopy", code: 403, userInfo: [NSLocalizedDescriptionKey: "Consent expired"])
        }
        
        guard (200...299).contains(http.statusCode) else {
            throw NSError(domain: "Teloscopy", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: "Server error: \(http.statusCode)"])
        }
        
        return try JSONDecoder().decode(CounselResponse.self, from: data)
    }
    
    func clearChat() {
        messages.removeAll()
        currentTheme = ""
        error = nil
    }
    
    func clearError() {
        error = nil
    }
}
