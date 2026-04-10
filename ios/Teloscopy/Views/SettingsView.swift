// SettingsView.swift
// Teloscopy
//
// Application settings: server configuration, notifications,
// appearance, data management, and about information.
//

import SwiftUI
import Combine

struct SettingsView: View {
    @EnvironmentObject var apiService: APIService
    @EnvironmentObject var syncManager: SyncManager
    
    @AppStorage("server_url") private var serverURL = APIConfiguration.defaultBaseURL
    @AppStorage("appearance_mode") private var appearanceMode = "system"
    @AppStorage("notifications_enabled") private var notificationsEnabled = true
    @AppStorage("notification_analysis_complete") private var notifyAnalysisComplete = true
    @AppStorage("notification_sync_errors") private var notifySyncErrors = true
    @AppStorage("auto_sync_enabled") private var autoSyncEnabled = true
    @AppStorage("auto_upload_on_wifi") private var autoUploadOnWifi = true
    @AppStorage("image_compression_quality") private var compressionQuality = 0.85
    @AppStorage("keep_local_images") private var keepLocalImages = true
    
    @State private var showServerURLEditor = false
    @State private var tempServerURL = ""
    @State private var isTestingConnection = false
    @State private var connectionTestResult: ConnectionTestResult?
    @State private var showClearCacheConfirm = false
    @State private var showResetConfirm = false
    @State private var showLogoutConfirm = false
    @State private var cancellables = Set<AnyCancellable>()
    
    enum ConnectionTestResult {
        case success
        case failure(String)
    }
    
    @AppStorage("consent_accepted") private var consentAccepted = true
    @State private var showWithdrawConsentConfirm = false
    
    var body: some View {
        List {
            serverSection
            accountSection
            syncSection
            notificationSection
            appearanceSection
            dataSection
            privacyLegalSection
            aboutSection
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Settings")
        .sheet(isPresented: $showServerURLEditor) {
            serverURLEditor
        }
        .alert("Clear Cache?", isPresented: $showClearCacheConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Clear", role: .destructive) {
                syncManager.clearCache()
            }
        } message: {
            Text("This will remove all locally cached analyses and results. Synced data on the server will not be affected.")
        }
        .alert("Reset All Settings?", isPresented: $showResetConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Reset", role: .destructive) { resetAllSettings() }
        } message: {
            Text("This will reset all settings to their default values. Your analysis data will not be affected.")
        }
        .alert("Sign Out?", isPresented: $showLogoutConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Sign Out", role: .destructive) {
                apiService.logout()
            }
        } message: {
            Text("You'll need to sign in again to sync your data.")
        }
        .alert("Withdraw Consent?", isPresented: $showWithdrawConsentConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Withdraw", role: .destructive) {
                consentAccepted = false
                UserDefaults.standard.removeObject(forKey: "consent_timestamp")
                UserDefaults.standard.removeObject(forKey: "research_consent")
                UserDefaults.standard.removeObject(forKey: "consent_version")
            }
        } message: {
            Text("Withdrawing consent will return you to the consent screen. You will need to re-accept the terms to continue using Teloscopy. As per the DPDP Act, 2023, this does not affect the lawfulness of processing done prior to withdrawal.")
        }
    }
    
    // MARK: - Server Configuration
    
    private var serverSection: some View {
        Section {
            // Server URL
            Button(action: {
                tempServerURL = serverURL
                showServerURLEditor = true
            }) {
                HStack {
                    Label {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Server URL")
                                .font(.subheadline)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                            Text(serverURL)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                                .lineLimit(1)
                        }
                    } icon: {
                        Image(systemName: "server.rack")
                            .foregroundColor(TeloscopyTheme.primaryBlue)
                    }
                    
                    Spacer()
                    
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
            }
            
            // Connection status
            HStack {
                Label {
                    Text("Connection Status")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: apiService.isServerReachable ? "wifi" : "wifi.slash")
                        .foregroundColor(apiService.isServerReachable ? TeloscopyTheme.successGreen : TeloscopyTheme.errorRed)
                }
                
                Spacer()
                
                if isTestingConnection {
                    ProgressView()
                        .scaleEffect(0.8)
                } else {
                    Text(apiService.isServerReachable ? "Connected" : "Disconnected")
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(apiService.isServerReachable ? TeloscopyTheme.successGreen : TeloscopyTheme.errorRed)
                }
            }
            
            // Test connection button
            Button(action: testConnection) {
                Label("Test Connection", systemImage: "arrow.triangle.2.circlepath")
                    .font(.subheadline)
            }
            .disabled(isTestingConnection)
            
            if let result = connectionTestResult {
                switch result {
                case .success:
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(TeloscopyTheme.successGreen)
                        Text("Connection successful")
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.successGreen)
                    }
                case .failure(let message):
                    HStack {
                        Image(systemName: "exclamationmark.circle.fill")
                            .foregroundColor(TeloscopyTheme.errorRed)
                        Text(message)
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.errorRed)
                    }
                }
            }
        } header: {
            Text("Server Configuration")
        } footer: {
            Text("Configure the Teloscopy analysis server address. Default: \(APIConfiguration.defaultBaseURL)")
        }
    }
    
    // MARK: - Account Section
    
    private var accountSection: some View {
        Section("Account") {
            if apiService.isAuthenticated, let user = apiService.currentUser {
                HStack {
                    Label {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(user.fullName)
                                .font(.subheadline)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                            Text(user.email)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                        }
                    } icon: {
                        ZStack {
                            Circle()
                                .fill(TeloscopyTheme.primaryBlue.opacity(0.15))
                                .frame(width: 32, height: 32)
                            Text(user.fullName.prefix(1).uppercased())
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.primaryBlue)
                        }
                    }
                }
                
                Button(role: .destructive, action: { showLogoutConfirm = true }) {
                    Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                        .font(.subheadline)
                }
            } else {
                Button(action: { }) {
                    Label("Sign In", systemImage: "person.crop.circle")
                        .font(.subheadline)
                }
            }
        }
    }
    
    // MARK: - Sync Section
    
    private var syncSection: some View {
        Section {
            Toggle(isOn: $autoSyncEnabled) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Auto Sync")
                            .font(.subheadline)
                        Text("Periodically sync with server")
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                    }
                } icon: {
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .foregroundColor(TeloscopyTheme.primaryBlue)
                }
            }
            .tint(TeloscopyTheme.primaryBlue)
            
            Toggle(isOn: $autoUploadOnWifi) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Upload on Wi-Fi Only")
                            .font(.subheadline)
                        Text("Save cellular data")
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                    }
                } icon: {
                    Image(systemName: "wifi")
                        .foregroundColor(TeloscopyTheme.accentTeal)
                }
            }
            .tint(TeloscopyTheme.primaryBlue)
            
            // Pending uploads
            HStack {
                Label {
                    Text("Pending Uploads")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "arrow.up.circle")
                        .foregroundColor(TeloscopyTheme.warningOrange)
                }
                
                Spacer()
                
                Text("\(syncManager.pendingUploads.count)")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            // Sync now button
            Button(action: { syncManager.performSync() }) {
                HStack {
                    Label("Sync Now", systemImage: "arrow.clockwise")
                        .font(.subheadline)
                    
                    Spacer()
                    
                    if syncManager.syncState == .syncing {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Text(syncManager.syncState.displayName)
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                    }
                }
            }
            .disabled(syncManager.syncState == .syncing)
        } header: {
            Text("Data Sync")
        }
    }
    
    // MARK: - Notifications Section
    
    private var notificationSection: some View {
        Section {
            Toggle(isOn: $notificationsEnabled) {
                Label {
                    Text("Enable Notifications")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "bell.fill")
                        .foregroundColor(TeloscopyTheme.warningOrange)
                }
            }
            .tint(TeloscopyTheme.primaryBlue)
            
            if notificationsEnabled {
                Toggle(isOn: $notifyAnalysisComplete) {
                    Label {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Analysis Complete")
                                .font(.subheadline)
                            Text("Notify when results are ready")
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                        }
                    } icon: {
                        Image(systemName: "checkmark.circle")
                            .foregroundColor(TeloscopyTheme.successGreen)
                    }
                }
                .tint(TeloscopyTheme.primaryBlue)
                
                Toggle(isOn: $notifySyncErrors) {
                    Label {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Sync Errors")
                                .font(.subheadline)
                            Text("Notify on upload or sync failures")
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                        }
                    } icon: {
                        Image(systemName: "exclamationmark.triangle")
                            .foregroundColor(TeloscopyTheme.errorRed)
                    }
                }
                .tint(TeloscopyTheme.primaryBlue)
            }
        } header: {
            Text("Notifications")
        }
    }
    
    // MARK: - Appearance Section
    
    private var appearanceSection: some View {
        Section {
            Picker(selection: $appearanceMode) {
                Text("System").tag("system")
                Text("Light").tag("light")
                Text("Dark").tag("dark")
            } label: {
                Label {
                    Text("Appearance")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "paintbrush.fill")
                        .foregroundColor(TeloscopyTheme.primaryBlue)
                }
            }
            
            VStack(alignment: .leading, spacing: 8) {
                Label {
                    Text("Image Compression")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "photo")
                        .foregroundColor(TeloscopyTheme.accentTeal)
                }
                
                HStack {
                    Slider(value: $compressionQuality, in: 0.5...1.0, step: 0.05)
                        .tint(TeloscopyTheme.primaryBlue)
                    
                    Text("\(Int(compressionQuality * 100))%")
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                        .frame(width: 40)
                }
            }
            
            Toggle(isOn: $keepLocalImages) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Keep Local Images")
                            .font(.subheadline)
                        Text("Retain images after upload")
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                    }
                } icon: {
                    Image(systemName: "internaldrive")
                        .foregroundColor(TeloscopyTheme.warningOrange)
                }
            }
            .tint(TeloscopyTheme.primaryBlue)
        } header: {
            Text("Appearance & Storage")
        }
    }
    
    // MARK: - Data Management Section
    
    private var dataSection: some View {
        Section {
            // Cache size
            HStack {
                Label {
                    Text("Cache Size")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "internaldrive")
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                
                Spacer()
                
                Text(syncManager.cacheSize)
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            Button(action: { showClearCacheConfirm = true }) {
                Label("Clear Cache", systemImage: "trash")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.warningOrange)
            }
            
            if !syncManager.pendingUploads.isEmpty {
                Button(action: { syncManager.clearUploadQueue() }) {
                    Label("Clear Upload Queue", systemImage: "xmark.circle")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.errorRed)
                }
            }
            
            Button(action: { showResetConfirm = true }) {
                Label("Reset All Settings", systemImage: "arrow.counterclockwise")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.errorRed)
            }
        } header: {
            Text("Data Management")
        }
    }
    
    // MARK: - Privacy & Legal Section
    
    private var privacyLegalSection: some View {
        Section {
            // Consent status
            HStack {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Consent Status")
                            .font(.subheadline)
                            .foregroundColor(TeloscopyTheme.textPrimary)
                        if let timestamp = UserDefaults.standard.string(forKey: "consent_timestamp") {
                            Text("Accepted: \(timestamp)")
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                        }
                    }
                } icon: {
                    Image(systemName: "checkmark.shield.fill")
                        .foregroundColor(TeloscopyTheme.successGreen)
                }
                
                Spacer()
                
                Text("Active")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.successGreen)
            }
            
            // Privacy Policy link
            NavigationLink {
                privacyPolicyView
            } label: {
                Label {
                    Text("Privacy Policy")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "hand.raised.fill")
                        .foregroundColor(TeloscopyTheme.primaryBlue)
                }
            }
            
            // Terms of Service link
            NavigationLink {
                termsOfServiceView
            } label: {
                Label {
                    Text("Terms of Service")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "doc.plaintext.fill")
                        .foregroundColor(TeloscopyTheme.primaryBlue)
                }
            }
            
            // Grievance officer contact
            HStack {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Grievance Officer")
                            .font(.subheadline)
                            .foregroundColor(TeloscopyTheme.textPrimary)
                        Text("animaticalpha123@gmail.com")
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.primaryBlue)
                    }
                } icon: {
                    Image(systemName: "person.badge.shield.checkmark.fill")
                        .foregroundColor(TeloscopyTheme.accentTeal)
                }
            }
            
            // Withdraw consent button
            Button(action: { showWithdrawConsentConfirm = true }) {
                Label("Withdraw Consent", systemImage: "xmark.shield.fill")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.errorRed)
            }
        } header: {
            Text("Privacy & Legal")
        } footer: {
            Text("Your data rights are protected under the Digital Personal Data Protection Act, 2023 (India). Contact the Grievance Officer for any concerns.")
        }
    }
    
    private var termsOfServiceView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Terms of Service")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("Effective Date: 1 January 2026  |  Version: 1.0")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                
                Group {
                    Text("1. Acceptance of Terms")
                        .font(.headline)
                    Text("By accessing, downloading, installing, or using the Teloscopy application, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service. If you do not agree, you must discontinue use of the application immediately.")
                    
                    Text("2. Eligibility")
                        .font(.headline)
                    Text("You must be at least 18 years of age to use Teloscopy. This restriction is mandated by the nature of the sensitive personal data processed, including health data and genetic information, which constitutes sensitive personal data under Section 9 of the Digital Personal Data Protection Act, 2023.")
                    
                    Text("3. Service Description")
                        .font(.headline)
                    Text("Teloscopy is an open-source, multi-agent genomic intelligence platform that provides:\n\u{2022} Telomere analysis and biological age estimation from microscopy images\n\u{2022} Disease risk prediction using genetic variants and demographic data\n\u{2022} Personalised nutrition and diet recommendations\n\u{2022} Facial-genomic analysis (biological age, ancestry, pharmacogenomics)\n\u{2022} Health checkup analysis from uploaded blood/urine/scan reports\n\u{2022} Downloadable reports in HTML, JSON, and CSV formats")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
                
                // Medical Disclaimer - highlighted
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(TeloscopyTheme.warningOrange)
                        Text("4. Medical Disclaimer")
                            .font(.headline)
                            .foregroundColor(TeloscopyTheme.warningOrange)
                    }
                    
                    Text("Teloscopy is NOT a medical device as defined under the Medical Devices Rules, 2017. It is NOT registered with or approved by the Central Drugs Standard Control Organisation (CDSCO), the Drug Controller General of India (DCGI), or any other regulatory authority.\n\nResults are statistical correlations derived from published research and are NOT clinical diagnoses. Biological age estimations carry significant uncertainty. Nutritional recommendations are general wellness guidance, not medical prescriptions. Pharmacogenomic predictions are statistical estimates, not clinical testing.\n\nYou MUST NOT use results for self-diagnosis, self-medication, delaying medical treatment, insurance decisions, employment decisions, legal purposes, or reproductive planning without professional guidance.\n\nAlways consult a qualified registered medical practitioner for all health-related decisions.")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .padding()
                .background(TeloscopyTheme.warningOrange.opacity(0.08))
                .overlay(
                    RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                        .stroke(TeloscopyTheme.warningOrange.opacity(0.3), lineWidth: 1)
                )
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
                
                Group {
                    Text("5. Genetic Information Notice")
                        .font(.headline)
                    Text("Self-reported genetic variants may be incomplete or based on consumer-grade testing. Facial-to-genetic predictions are statistical estimates with significant uncertainty. DNA sequence reconstructions are approximate computational outputs, NOT equivalent to actual DNA sequencing, and must not be submitted to clinical databases.")
                    
                    Text("6. Health Report Upload Terms")
                        .font(.headline)
                    Text("By uploading a health report, you represent that you are the Data Principal to whom the report pertains or have lawful authorisation. Reports are processed in server memory only and are not stored after analysis. Extracted values may contain OCR/parsing errors and must be verified against original reports.")
                    
                    Text("7. User Obligations")
                        .font(.headline)
                    Text("\u{2022} Provide accurate and truthful information\n\u{2022} Not misuse the platform for purposes prohibited in these Terms\n\u{2022} Not attempt to reverse-engineer, decompile, or circumvent security measures\n\u{2022} Acknowledge the research and educational nature of the platform\n\u{2022} Not upload health reports belonging to other individuals without authorisation")
                    
                    Text("8. Privacy and Data Protection")
                        .font(.headline)
                    Text("Your use of Teloscopy is governed by our Privacy Policy, which describes how we collect, process, and protect your Personal Data in compliance with the DPDP Act, 2023 and IT Act, 2000.")
                    
                    Text("9. Intellectual Property")
                        .font(.headline)
                    Text("Teloscopy is open-source software licensed under the MIT License. The source code is available at github.com/Mahesh2023/teloscopy. All analysis results generated for you belong to you.")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
                
                Group {
                    Text("10. Limitation of Liability")
                        .font(.headline)
                    Text("TO THE MAXIMUM EXTENT PERMITTED BY LAW, Teloscopy and its contributors shall not be liable for any direct, indirect, incidental, special, consequential, or punitive damages arising from your use of or inability to use the platform, reliance on any results or recommendations, or any errors in data extraction or analysis.")
                    
                    Text("11. Governing Law & Jurisdiction")
                        .font(.headline)
                    Text("These Terms are governed by the laws of India, including the Digital Personal Data Protection Act (2023), Information Technology Act (2000), and Consumer Protection Act (2019). Disputes shall first be attempted through mediation; if unresolved, they are subject to the exclusive jurisdiction of courts in India.")
                    
                    Text("12. Contact Information")
                        .font(.headline)
                    Text("For questions about these Terms:\n\nEmail: animaticalpha123@gmail.com\nGitHub: github.com/Mahesh2023/teloscopy")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            }
            .padding()
        }
        .navigationTitle("Terms of Service")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    // MARK: - About Section
    
    private var aboutSection: some View {
        Section {
            HStack {
                Label {
                    Text("Version")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "info.circle")
                        .foregroundColor(TeloscopyTheme.primaryBlue)
                }
                Spacer()
                Text("1.0.0 (1)")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            HStack {
                Label {
                    Text("Bundle ID")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "shippingbox")
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                Spacer()
                Text("com.teloscopy.ios")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            HStack {
                Label {
                    Text("iOS Target")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "iphone")
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                Spacer()
                Text("iOS 16.0+")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }
            
            NavigationLink {
                licensesView
            } label: {
                Label {
                    Text("Open Source Licenses")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "doc.text")
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
            }
            
            NavigationLink {
                privacyPolicyView
            } label: {
                Label {
                    Text("Privacy Policy")
                        .font(.subheadline)
                } icon: {
                    Image(systemName: "hand.raised.fill")
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
            }
        } header: {
            Text("About")
        } footer: {
            VStack(spacing: 4) {
                Text("Teloscopy - Genomic Telomere Analysis")
                Text("Built with SwiftUI for iOS 16+")
            }
            .font(.caption2)
            .frame(maxWidth: .infinity)
            .padding(.top, 12)
        }
    }
    
    // MARK: - Server URL Editor Sheet
    
    private var serverURLEditor: some View {
        NavigationStack {
            VStack(spacing: 24) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Server URL")
                        .font(.headline)
                    
                    Text("Enter the address of your Teloscopy analysis server.")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                    
                    TextField("https://your-server.example.com", text: $tempServerURL)
                        .textFieldStyle(.plain)
                        .padding(14)
                        .background(TeloscopyTheme.surfaceBackground)
                        .cornerRadius(TeloscopyTheme.smallCornerRadius)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    
                    Text("Default: \(APIConfiguration.defaultBaseURL)")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                
                Button("Reset to Default") {
                    tempServerURL = APIConfiguration.defaultBaseURL
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.primaryBlue)
                
                Spacer()
            }
            .padding()
            .navigationTitle("Server URL")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        showServerURLEditor = false
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        serverURL = tempServerURL
                        showServerURLEditor = false
                        // Recheck connection with new URL
                        testConnection()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
    }
    
    // MARK: - Licenses View
    
    private var licensesView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Open Source Licenses")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("Teloscopy iOS uses the following open source technologies:")
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                
                VStack(alignment: .leading, spacing: 12) {
                    LicenseRow(name: "SwiftUI", license: "Apple Inc. - Proprietary")
                    LicenseRow(name: "Combine", license: "Apple Inc. - Proprietary")
                    LicenseRow(name: "Foundation", license: "Apple Inc. - Proprietary")
                }
                
                Text("This application is built entirely using Apple's first-party frameworks with no third-party dependencies.")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                    .padding(.top)
            }
            .padding()
        }
        .navigationTitle("Licenses")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private var privacyPolicyView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Privacy Policy")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("Last updated: July 1, 2025")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                
                Group {
                    Text("1. Introduction")
                        .font(.headline)
                    Text("This Privacy Policy describes how Teloscopy (\"we\", \"us\", or \"the App\") collects, uses, processes, stores, and protects your Personal Data and Sensitive Personal Data or Information (SPDI). We act as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (DPDP Act) of India.")
                    
                    Text("2. Data We Collect")
                        .font(.headline)
                    
                    Text("Sensitive Personal Data (SPDI):")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text("\u{2022} Facial photographs (biometric data) for age-related and genomic analysis\n\u{2022} Health reports (blood tests, urine tests, abdomen scans) uploaded for health checkup analysis\n\u{2022} Self-reported genetic variant data (SNP genotypes) for disease risk and pharmacogenomic analysis\n\u{2022} Telomere length measurements from microscopy images\n\u{2022} Health conditions and medical dietary restrictions")
                    
                    Text("Regular Personal Data:")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text("\u{2022} Demographic data: age, biological sex, geographic region\n\u{2022} Dietary preferences and restrictions\n\u{2022} App preferences (theme, server URL) stored locally on your device")
                    
                    Text("Data We Do NOT Collect:")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text("We do not collect device identifiers, location data, contacts, browsing history, financial data, or any data from other applications. No third-party analytics or advertising SDKs are used.")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
                
                Group {
                    Text("3. How We Use Your Data")
                        .font(.headline)
                    Text("Your data is used exclusively to:\n\u{2022} Perform telomere analysis and biological age estimation\n\u{2022} Compute disease risk assessments from genetic variants and health data\n\u{2022} Generate personalised nutrition and meal plan recommendations\n\u{2022} Analyse facial photographs for genomic and health insights\n\u{2022} Parse and interpret uploaded health checkup reports\n\u{2022} Display analysis results within the App\n\nWe do NOT use your data for advertising, profiling, marketing, training machine learning models on individual data, or sharing with third parties.")
                    
                    Text("4. Consent")
                        .font(.headline)
                    Text("In accordance with Section 6 of the DPDP Act, 2023, we obtain explicit, freely given, informed, specific, and unambiguous consent before processing any Personal Data. Separate consent is obtained for facial image processing, health report upload, and genetic data processing. You may withdraw consent at any time through the Settings screen or by contacting us at animaticalpha123@gmail.com.")
                    
                    Text("5. Data Processing & Storage")
                        .font(.headline)
                    Text("\u{2022} On-device: App preferences are stored locally. No health data is cached after you leave the results screen.\n\u{2022} Server-side: All Sensitive Personal Data (images, health reports, genetic data) is processed in server memory only and is NOT written to disk or any persistent storage.\n\u{2022} No cloud storage: We do not store your data on any external cloud service or database beyond the duration of a single analysis request.")
                    
                    Text("6. Data Security")
                        .font(.headline)
                    Text("All network communication uses HTTPS/TLS 1.2+ encryption. Sensitive data is processed entirely in server memory and never written to disk. Security practices are aligned with IS/ISO/IEC 27001 principles.")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
                
                Group {
                    Text("7. Your Rights (DPDP Act, Sections 11-14)")
                        .font(.headline)
                    Text("As a Data Principal, you have the right to:\n\u{2022} Access: Obtain a summary of your Personal Data and processing activities (Section 11)\n\u{2022} Correction & Erasure: Correct inaccurate data or request erasure (Section 12)\n\u{2022} Grievance Redressal: Lodge a grievance with our Grievance Officer (Section 13)\n\u{2022} Nomination: Nominate an individual to exercise your rights (Section 14)\n\u{2022} Complain to the Data Protection Board of India if a grievance is not resolved")
                    
                    Text("8. Children's Privacy")
                        .font(.headline)
                    Text("Teloscopy is not intended for use by individuals under 18 years of age (as defined under Section 9, DPDP Act). We do not knowingly collect data from children.")
                    
                    Text("9. Medical Disclaimer")
                        .font(.headline)
                    Text("Teloscopy is NOT a medical device and is not registered under the Drugs & Cosmetics Act, 1940 or with CDSCO. Results are statistical estimates for research and educational purposes only. Always consult a qualified healthcare professional for medical decisions.")
                    
                    Text("10. Grievance Officer & Contact")
                        .font(.headline)
                    Text("For any concerns regarding your personal data or to exercise your rights:\n\nGrievance Officer: Mahesh (Project Maintainer)\nEmail: animaticalpha123@gmail.com\nGitHub: github.com/Mahesh2023/teloscopy\nResponse: Acknowledgement within 48 hours; resolution within 30 days\n\nEscalation: Data Protection Board of India (Section 18, DPDP Act)")
                    
                    Text("11. Governing Law")
                        .font(.headline)
                    Text("This Policy is governed by the laws of India, including the Digital Personal Data Protection Act (2023), Information Technology Act (2000), IT Rules (2011), and the Consumer Protection Act (2019). Disputes are subject to the exclusive jurisdiction of courts in India.")
                }
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textSecondary)
            }
            .padding()
        }
        .navigationTitle("Privacy Policy")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    // MARK: - Actions
    
    private func testConnection() {
        isTestingConnection = true
        connectionTestResult = nil
        
        apiService.checkServerHealth()
            .receive(on: DispatchQueue.main)
            .sink { reachable in
                isTestingConnection = false
                connectionTestResult = reachable ? .success : .failure("Could not reach the server. Verify the URL and that the server is running.")
            }
            .store(in: &cancellables)
    }
    
    private func resetAllSettings() {
        serverURL = APIConfiguration.defaultBaseURL
        appearanceMode = "system"
        notificationsEnabled = true
        notifyAnalysisComplete = true
        notifySyncErrors = true
        autoSyncEnabled = true
        autoUploadOnWifi = true
        compressionQuality = 0.85
        keepLocalImages = true
    }
}

// MARK: - License Row

struct LicenseRow: View {
    let name: String
    let license: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(name)
                .font(.subheadline)
                .fontWeight(.semibold)
            Text(license)
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(TeloscopyTheme.surfaceBackground)
        .cornerRadius(TeloscopyTheme.smallCornerRadius)
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        SettingsView()
    }
    .environmentObject(APIService.shared)
    .environmentObject(SyncManager.shared)
}
