// ConsentView.swift
// Teloscopy
//
// Legal compliance consent screen for Indian data protection regulations.
// Implements DPDP Act 2023 and IT Act 2000 requirements including
// informed consent, data principal rights, and grievance redressal.
//

import SwiftUI

struct ConsentView: View {
    var onAccept: () -> Void
    
    // MARK: - Required Consent Toggles
    
    @State private var ageConfirmed = false
    @State private var privacyPolicyAccepted = false
    @State private var termsAccepted = false
    @State private var dataProcessingConsent = false
    
    // MARK: - Optional Consent Toggles
    
    @State private var researchConsent = false
    
    // MARK: - UI State
    
    @State private var showDeclineAlert = false
    
    private var allRequiredAccepted: Bool {
        ageConfirmed && privacyPolicyAccepted && termsAccepted && dataProcessingConsent
    }
    
    // MARK: - Body
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    headerSection
                    privacyNoticeSection
                    dataCollectionSection
                    dataPrincipalRightsSection
                    medicalDisclaimerSection
                    consentTogglesSection
                    optionalConsentSection
                    grievanceOfficerSection
                    actionButtonsSection
                }
                .padding()
            }
            .background(TeloscopyTheme.surfaceBackground.ignoresSafeArea())
            .navigationTitle("Consent & Privacy")
            .navigationBarTitleDisplayMode(.inline)
            .alert("Consent Required", isPresented: $showDeclineAlert) {
                Button("Review Again", role: .cancel) { }
            } message: {
                Text("Teloscopy requires your informed consent to process sensitive health and genetic data as mandated by the Digital Personal Data Protection Act, 2023. The app cannot function without this consent. Please review the terms and provide your consent to continue.")
            }
        }
    }
    
    // MARK: - Header
    
    private var headerSection: some View {
        VStack(spacing: 12) {
            Image(systemName: "hand.raised.fill")
                .font(.system(size: 48))
                .foregroundStyle(
                    LinearGradient(
                        colors: [TeloscopyTheme.primaryBlue, TeloscopyTheme.accentTeal],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            
            Text("Privacy & Consent")
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(TeloscopyTheme.textPrimary)
            
            Text("Please review and accept the following before using Teloscopy")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 8)
    }
    
    // MARK: - Privacy Notice (DPDP Act Reference)
    
    private var privacyNoticeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label {
                Text("Privacy Notice")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "shield.checkered")
                    .foregroundColor(TeloscopyTheme.primaryBlue)
            }
            
            Text("This notice is provided in compliance with the **Digital Personal Data Protection (DPDP) Act, 2023** and the **Information Technology Act, 2000** of India.")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            
            Text("Teloscopy (\"Data Fiduciary\") processes your personal and sensitive personal data for genomic telomere analysis. As a Data Principal, you have specific rights under the DPDP Act which are outlined below.")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    // MARK: - Data Collection Details
    
    private var dataCollectionSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label {
                Text("Data We Collect")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "list.clipboard.fill")
                    .foregroundColor(TeloscopyTheme.accentTeal)
            }
            
            Text("The following categories of personal and sensitive personal data are collected and processed:")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            
            VStack(alignment: .leading, spacing: 8) {
                dataTypeRow(icon: "camera.fill", text: "Facial images for age-related analysis")
                dataTypeRow(icon: "heart.text.square.fill", text: "Health reports and medical history")
                dataTypeRow(icon: "dna", text: "Genetic variants and genomic data")
                dataTypeRow(icon: "person.fill", text: "Demographic information (age, sex, ethnicity)")
                dataTypeRow(icon: "ruler.fill", text: "Telomere length measurements")
                dataTypeRow(icon: "fork.knife", text: "Dietary and nutritional information")
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    private func dataTypeRow(icon: String, text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(TeloscopyTheme.primaryBlue)
                .frame(width: 20)
            
            Text(text)
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
    }
    
    // MARK: - Data Principal Rights
    
    private var dataPrincipalRightsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label {
                Text("Your Rights")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "checkmark.shield.fill")
                    .foregroundColor(TeloscopyTheme.successGreen)
            }
            
            Text("As a Data Principal under the DPDP Act, 2023, you have the following rights:")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            
            VStack(alignment: .leading, spacing: 8) {
                rightRow(title: "Right to Access", description: "Request a summary of your personal data being processed")
                rightRow(title: "Right to Correction", description: "Request correction of inaccurate or misleading data")
                rightRow(title: "Right to Erasure", description: "Request deletion of your personal data")
                rightRow(title: "Right to Grievance Redressal", description: "File complaints regarding data processing")
                rightRow(title: "Right to Nomination", description: "Nominate a person to exercise your rights")
                rightRow(title: "Right to Withdrawal", description: "Withdraw consent at any time via Settings")
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    private func rightRow(title: String, description: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "checkmark.circle.fill")
                .font(.caption)
                .foregroundColor(TeloscopyTheme.successGreen)
                .padding(.top, 2)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.textPrimary)
                Text(description)
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
        }
    }
    
    // MARK: - Medical Disclaimer
    
    private var medicalDisclaimerSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(TeloscopyTheme.warningOrange)
                Text("Medical Disclaimer")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.warningOrange)
            }
            
            Text("Teloscopy is a research and informational tool ONLY. Results from telomere analysis, genetic variant interpretation, and health assessments are NOT medical diagnoses and must NOT be used as a substitute for professional medical advice, diagnosis, or treatment.")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textPrimary)
            
            Text("Always consult a qualified healthcare provider for medical decisions. Teloscopy and its operators are not liable for any health decisions made based on the app's output.")
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.warningOrange.opacity(0.08))
        .overlay(
            RoundedRectangle(cornerRadius: TeloscopyTheme.cornerRadius)
                .stroke(TeloscopyTheme.warningOrange.opacity(0.3), lineWidth: 1)
        )
        .cornerRadius(TeloscopyTheme.cornerRadius)
    }
    
    // MARK: - Required Consent Toggles
    
    private var consentTogglesSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label {
                Text("Required Consent")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "lock.shield.fill")
                    .foregroundColor(TeloscopyTheme.primaryBlue)
            }
            
            consentToggle(
                isOn: $ageConfirmed,
                title: "Age Confirmation",
                description: "I confirm that I am 18 years of age or older, as required under Section 9 of the DPDP Act, 2023."
            )
            
            consentToggle(
                isOn: $privacyPolicyAccepted,
                title: "Privacy Policy",
                description: "I have read and understood the Teloscopy Privacy Policy, including how my personal and sensitive personal data will be collected, stored, and processed."
            )
            
            consentToggle(
                isOn: $termsAccepted,
                title: "Terms of Service",
                description: "I agree to the Teloscopy Terms of Service, including the limitations of liability and the dispute resolution mechanism."
            )
            
            consentToggle(
                isOn: $dataProcessingConsent,
                title: "Data Processing Consent",
                description: "I provide informed consent for Teloscopy to collect and process my personal data, including sensitive personal data (health, genetic, and biometric data), for the purpose of telomere analysis and related health insights."
            )
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    private func consentToggle(isOn: Binding<Bool>, title: String, description: String) -> some View {
        Toggle(isOn: isOn) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.textPrimary)
                Text(description)
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .tint(TeloscopyTheme.primaryBlue)
    }
    
    // MARK: - Optional Consent
    
    private var optionalConsentSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label {
                Text("Optional Consent")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "flask.fill")
                    .foregroundColor(TeloscopyTheme.accentTeal)
            }
            
            Toggle(isOn: $researchConsent) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Research Contribution")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(TeloscopyTheme.textPrimary)
                    Text("I consent to the use of my anonymized and de-identified data for improving Teloscopy's analysis models and contributing to telomere research. This is entirely optional and can be withdrawn at any time.")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .tint(TeloscopyTheme.accentTeal)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    // MARK: - Grievance Officer
    
    private var grievanceOfficerSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label {
                Text("Grievance Officer")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            } icon: {
                Image(systemName: "person.badge.shield.checkmark.fill")
                    .foregroundColor(TeloscopyTheme.primaryBlue)
            }
            
            Text("For any concerns regarding your personal data or to exercise your rights under the DPDP Act, please contact our Grievance Officer:")
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            
            HStack(spacing: 8) {
                Image(systemName: "envelope.fill")
                    .foregroundColor(TeloscopyTheme.primaryBlue)
                    .font(.caption)
                Text("animaticalpha123@gmail.com")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.primaryBlue)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(TeloscopyTheme.primaryBlue.opacity(0.08))
            .cornerRadius(TeloscopyTheme.smallCornerRadius)
            
            Text("We will acknowledge your request within 48 hours and resolve it within 30 days as per regulatory requirements.")
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.cardBackground)
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .shadow(color: TeloscopyTheme.cardShadow, radius: 8, x: 0, y: 2)
    }
    
    // MARK: - Action Buttons
    
    private var actionButtonsSection: some View {
        VStack(spacing: 12) {
            Button(action: acceptConsent) {
                HStack {
                    Image(systemName: "checkmark.shield.fill")
                    Text("I Agree & Continue")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(
                    LinearGradient(
                        colors: allRequiredAccepted
                            ? [TeloscopyTheme.primaryBlue, TeloscopyTheme.darkBlue]
                            : [Color.gray.opacity(0.4), Color.gray.opacity(0.3)],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .foregroundColor(.white)
                .cornerRadius(TeloscopyTheme.cornerRadius)
            }
            .disabled(!allRequiredAccepted)
            
            if !allRequiredAccepted {
                Text("Please accept all required consents above to continue")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            Button(action: { showDeclineAlert = true }) {
                Text("Decline")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.errorRed)
            }
            .padding(.top, 4)
            .padding(.bottom, 16)
        }
    }
    
    // MARK: - Actions
    
    private func acceptConsent() {
        guard allRequiredAccepted else { return }
        
        // Store consent details
        UserDefaults.standard.set(Date().ISO8601Format(), forKey: "consent_timestamp")
        UserDefaults.standard.set(researchConsent, forKey: "research_consent")
        UserDefaults.standard.set("1.0", forKey: "consent_version")
        
        onAccept()
    }
}

// MARK: - Preview

#Preview {
    ConsentView(onAccept: { })
}
