// HealthCheckupView.swift
// Teloscopy
//
// Comprehensive health checkup view: upload lab reports (PDF, PNG, JPG, TXT),
// extract biomarker values with preview, configure patient profile, and display
// full analysis results including health score, lab results, findings, diet
// recommendations, abdomen findings, detected conditions, and meal plans.
//

import SwiftUI
import UniformTypeIdentifiers

// MARK: - View State

private enum CheckupViewState: Equatable {
    case idle
    case parsing
    case parsed
    case analyzing
    case results
    case error(String)
}

// MARK: - Region Options

private let regionOptions = [
    "South Indian",
    "North Indian",
    "East Indian",
    "West Indian",
    "Northern Europe",
    "Southern Europe",
    "East Asia",
    "South Asia",
    "West Africa",
    "East Africa",
    "Middle East"
]

// MARK: - Health Checkup View

struct HealthCheckupView: View {
    @EnvironmentObject var apiService: APIService

    // View state
    @State private var viewState: CheckupViewState = .idle

    // File selection
    @State private var showFileImporter = false
    @State private var selectedFileData: Data?
    @State private var selectedFileName: String = ""
    @State private var selectedFileSize: Int = 0

    // Profile
    @State private var age: String = ""
    @State private var sex: String = "male"
    @State private var region: String = "South Indian"
    @State private var profileExpanded: Bool = true

    // Results
    @State private var parsePreview: ReportParsePreview?
    @State private var checkupResponse: HealthCheckupResponse?

    // UI toggles
    @State private var expandedFindings: Set<String> = []
    @State private var expandedAbdomenFindings: Set<String> = []
    @State private var expandedMealPlans: Set<String> = []
    @State private var showUnrecognizedLines = false

    // Computed helpers
    private var canAnalyze: Bool {
        selectedFileData != nil && !age.isEmpty && (Int(age) ?? 0) > 0
    }

    private var isLoading: Bool {
        viewState == .parsing || viewState == .analyzing
    }

    // MARK: - Body

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                fileUploadSection
                profileSection

                if viewState == .parsing || viewState == .analyzing {
                    loadingSection
                }

                if case .error(let message) = viewState {
                    errorCard(message: message)
                }

                if viewState == .parsed, let preview = parsePreview {
                    extractionPreviewSection(preview: preview)
                }

                if let response = checkupResponse {
                    resultsContent(response: response)
                }
            }
            .padding()
        }
        .background(TeloscopyTheme.surfaceBackground.ignoresSafeArea())
        .navigationTitle("Health Checkup")
        .navigationBarTitleDisplayMode(.large)
        .fileImporter(
            isPresented: $showFileImporter,
            allowedContentTypes: [.pdf, .png, .jpeg, .plainText],
            allowsMultipleSelection: false
        ) { result in
            handleFileImport(result)
        }
    }

    // MARK: - Results Content

    @ViewBuilder
    private func resultsContent(response: HealthCheckupResponse) -> some View {
        healthScoreSection(response: response)
        labResultsSection(response: response)
        healthFindingsSection(response: response)
        abdomenFindingsSection(response: response)
        detectedConditionsSection(response: response)

        if let diet = response.dietRecommendation {
            dietRecommendationSection(diet: diet)
        }

        dietaryModificationsSection(response: response)

        if let ayurvedic = response.ayurvedicAnalysis {
            ayurvedicAnalysisSection(ayurvedic: ayurvedic)
        }

        if let llmText = response.llmAnalysis, !llmText.isEmpty {
            llmAnalysisSection(text: llmText)
        }

        if let disclaimer = response.disclaimer, !disclaimer.isEmpty {
            disclaimerSection(text: disclaimer)
        }
    }

    // MARK: - File Upload Section

    private var fileUploadSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Upload Lab Report", systemImage: "doc.badge.arrow.up")
                .font(.headline)
                .foregroundColor(TeloscopyTheme.textPrimary)

            VStack(spacing: 16) {
                // Format info
                HStack(spacing: 6) {
                    Image(systemName: "info.circle")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.accentTeal)

                    Text("Supported formats: PDF, PNG, JPG, TXT")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)

                    Spacer()
                }

                // File picker area
                if selectedFileData == nil {
                    Button(action: { showFileImporter = true }) {
                        VStack(spacing: 14) {
                            Image(systemName: "arrow.up.doc.fill")
                                .font(.system(size: 36))
                                .foregroundColor(TeloscopyTheme.primaryBlue.opacity(0.5))

                            Text("Tap to select a lab report")
                                .font(.subheadline)
                                .foregroundColor(TeloscopyTheme.textSecondary)

                            Text("Choose a file from your device")
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary.opacity(0.7))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 32)
                        .background(
                            RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                                .strokeBorder(
                                    style: StrokeStyle(lineWidth: 2, dash: [8, 4])
                                )
                                .foregroundColor(TeloscopyTheme.primaryBlue.opacity(0.3))
                        )
                    }
                    .buttonStyle(.plain)
                } else {
                    // Selected file info
                    HStack(spacing: 12) {
                        ZStack {
                            Circle()
                                .fill(TeloscopyTheme.successGreen.opacity(0.15))
                                .frame(width: 44, height: 44)

                            Image(systemName: fileIcon(for: selectedFileName))
                                .font(.system(size: 18))
                                .foregroundColor(TeloscopyTheme.successGreen)
                        }

                        VStack(alignment: .leading, spacing: 3) {
                            Text(selectedFileName)
                                .font(.subheadline)
                                .fontWeight(.medium)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                                .lineLimit(1)

                            Text(formattedFileSize(selectedFileSize))
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                        }

                        Spacer()

                        Button(action: clearFile) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title3)
                                .foregroundColor(TeloscopyTheme.textSecondary.opacity(0.6))
                        }
                    }
                    .padding()
                    .background(TeloscopyTheme.successGreen.opacity(0.05))
                    .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    .overlay(
                        RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                            .stroke(TeloscopyTheme.successGreen.opacity(0.3), lineWidth: 1)
                    )
                }

                // Action buttons
                if selectedFileData != nil {
                    HStack(spacing: 12) {
                        Button(action: extractValues) {
                            HStack(spacing: 6) {
                                if viewState == .parsing {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: TeloscopyTheme.primaryBlue))
                                        .scaleEffect(0.8)
                                } else {
                                    Image(systemName: "doc.text.magnifyingglass")
                                }
                                Text("Extract Values")
                                    .fontWeight(.medium)
                            }
                            .font(.subheadline)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 13)
                            .background(TeloscopyTheme.primaryBlue.opacity(0.1))
                            .foregroundColor(TeloscopyTheme.primaryBlue)
                            .cornerRadius(TeloscopyTheme.smallCornerRadius)
                            .overlay(
                                RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                                    .stroke(TeloscopyTheme.primaryBlue.opacity(0.3), lineWidth: 1)
                            )
                        }
                        .disabled(isLoading)

                        Button(action: uploadAndAnalyze) {
                            HStack(spacing: 6) {
                                if viewState == .analyzing {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                        .scaleEffect(0.8)
                                } else {
                                    Image(systemName: "waveform.path.ecg")
                                }
                                Text("Upload & Analyse")
                                    .fontWeight(.medium)
                            }
                            .font(.subheadline)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 13)
                            .background(
                                LinearGradient(
                                    colors: canAnalyze
                                        ? [TeloscopyTheme.primaryBlue, TeloscopyTheme.darkBlue]
                                        : [Color.gray.opacity(0.4), Color.gray.opacity(0.3)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .foregroundColor(.white)
                            .cornerRadius(TeloscopyTheme.smallCornerRadius)
                        }
                        .disabled(!canAnalyze || isLoading)
                    }
                }
            }
            .padding()
            .cardStyle()
        }
    }

    // MARK: - Profile Section (Collapsible)

    private var profileSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    profileExpanded.toggle()
                }
            }) {
                HStack {
                    Label("Patient Profile", systemImage: "person.text.rectangle")
                        .font(.headline)
                        .foregroundColor(TeloscopyTheme.textPrimary)

                    Spacer()

                    Image(systemName: profileExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
            }
            .buttonStyle(.plain)

            if profileExpanded {
                VStack(spacing: 16) {
                    // Age
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Age", systemImage: "calendar")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(TeloscopyTheme.textSecondary)

                        TextField("Enter age (e.g., 35)", text: $age)
                            .keyboardType(.numberPad)
                            .textFieldStyle(.plain)
                            .padding(12)
                            .background(TeloscopyTheme.surfaceBackground)
                            .cornerRadius(TeloscopyTheme.smallCornerRadius)
                            .overlay(
                                RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                                    .stroke(Color.gray.opacity(0.15), lineWidth: 1)
                            )
                    }

                    // Sex
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Sex", systemImage: "figure.stand")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(TeloscopyTheme.textSecondary)

                        Picker("Sex", selection: $sex) {
                            Text("Male").tag("male")
                            Text("Female").tag("female")
                        }
                        .pickerStyle(.segmented)
                    }

                    // Region
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Region", systemImage: "globe.asia.australia")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(TeloscopyTheme.textSecondary)

                        Menu {
                            ForEach(regionOptions, id: \.self) { option in
                                Button(action: { region = option }) {
                                    HStack {
                                        Text(option)
                                        if region == option {
                                            Image(systemName: "checkmark")
                                        }
                                    }
                                }
                            }
                        } label: {
                            HStack {
                                Text(region)
                                    .foregroundColor(TeloscopyTheme.textPrimary)

                                Spacer()

                                Image(systemName: "chevron.up.chevron.down")
                                    .font(.caption)
                                    .foregroundColor(TeloscopyTheme.textSecondary)
                            }
                            .padding(12)
                            .background(TeloscopyTheme.surfaceBackground)
                            .cornerRadius(TeloscopyTheme.smallCornerRadius)
                            .overlay(
                                RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                                    .stroke(Color.gray.opacity(0.15), lineWidth: 1)
                            )
                        }
                    }
                }
                .padding()
                .cardStyle()
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    // MARK: - Loading Section

    private var loadingSection: some View {
        VStack(spacing: 16) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: TeloscopyTheme.primaryBlue))
                .scaleEffect(1.3)

            Text(viewState == .parsing
                 ? "Extracting values from report..."
                 : "Analyzing your lab report...")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(TeloscopyTheme.textPrimary)

            Text(viewState == .parsing
                 ? "Parsing biomarkers and test values from your document"
                 : "Running comprehensive health analysis with dietary recommendations")
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 32)
        .padding(.horizontal)
        .cardStyle()
    }

    // MARK: - Error Card

    private func errorCard(message: String) -> some View {
        VStack(spacing: 14) {
            HStack(spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.title3)
                    .foregroundColor(TeloscopyTheme.errorRed)

                Text("Something went wrong")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Spacer()
            }

            Text(message)
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(TeloscopyTheme.errorRed.opacity(0.06))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)

            HStack(spacing: 12) {
                Button(action: retryLastAction) {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.clockwise")
                        Text("Retry")
                            .fontWeight(.medium)
                    }
                    .font(.subheadline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 11)
                    .background(TeloscopyTheme.primaryBlue.opacity(0.1))
                    .foregroundColor(TeloscopyTheme.primaryBlue)
                    .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    .overlay(
                        RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                            .stroke(TeloscopyTheme.primaryBlue.opacity(0.3), lineWidth: 1)
                    )
                }

                Button(action: dismissError) {
                    HStack(spacing: 6) {
                        Image(systemName: "xmark")
                        Text("Dismiss")
                            .fontWeight(.medium)
                    }
                    .font(.subheadline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 11)
                    .background(Color.gray.opacity(0.1))
                    .foregroundColor(TeloscopyTheme.textSecondary)
                    .cornerRadius(TeloscopyTheme.smallCornerRadius)
                }
            }
        }
        .padding()
        .background(TeloscopyTheme.errorRed.opacity(0.04))
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .overlay(
            RoundedRectangle(cornerRadius: TeloscopyTheme.cornerRadius)
                .stroke(TeloscopyTheme.errorRed.opacity(0.2), lineWidth: 1)
        )
    }

    // MARK: - Extraction Preview Section

    private func extractionPreviewSection(preview: ReportParsePreview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("Extraction Preview", systemImage: "doc.text.below.ecg")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Spacer()

                confidenceBadge(preview.confidence ?? 0)
            }

            VStack(spacing: 16) {
                // Count summary
                HStack(spacing: 16) {
                    let bloodCount = preview.extractedBloodTests?.count ?? 0
                    let urineCount = preview.extractedUrineTests?.count ?? 0

                    extractionCountChip(
                        count: bloodCount,
                        label: "blood",
                        color: TeloscopyTheme.errorRed
                    )

                    extractionCountChip(
                        count: urineCount,
                        label: "urine",
                        color: TeloscopyTheme.warningOrange
                    )

                    Spacer()

                    if let fileType = preview.fileType {
                        Text(fileType.uppercased())
                            .font(.caption2)
                            .fontWeight(.bold)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(TeloscopyTheme.accentTeal.opacity(0.15))
                            .foregroundColor(TeloscopyTheme.accentTeal)
                            .cornerRadius(6)
                    }
                }

                if let textLength = preview.textLength {
                    HStack(spacing: 4) {
                        Image(systemName: "text.alignleft")
                            .font(.caption2)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                        Text("\(textLength) characters parsed")
                            .font(.caption2)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                        Spacer()
                    }
                }

                Divider()

                // Blood test values
                if let bloodTests = preview.extractedBloodTests, !bloodTests.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Blood Tests", systemImage: "drop.fill")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.errorRed)

                        ForEach(Array(bloodTests.sorted(by: { $0.key < $1.key })), id: \.key) { key, value in
                            HStack {
                                Text(key)
                                    .font(.caption)
                                    .foregroundColor(TeloscopyTheme.textPrimary)

                                Spacer()

                                Text(String(format: "%.2f", value))
                                    .font(.caption)
                                    .fontWeight(.semibold)
                                    .foregroundColor(TeloscopyTheme.primaryBlue)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }

                // Urine test values
                if let urineTests = preview.extractedUrineTests, !urineTests.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Urine Tests", systemImage: "testtube.2")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.warningOrange)

                        ForEach(Array(urineTests.sorted(by: { $0.key < $1.key })), id: \.key) { key, value in
                            HStack {
                                Text(key)
                                    .font(.caption)
                                    .foregroundColor(TeloscopyTheme.textPrimary)

                                Spacer()

                                Text(String(format: "%.2f", value))
                                    .font(.caption)
                                    .fontWeight(.semibold)
                                    .foregroundColor(TeloscopyTheme.primaryBlue)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }

                // Abdomen notes
                if let abdomenNotes = preview.extractedAbdomenNotes, !abdomenNotes.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Abdomen Notes", systemImage: "note.text")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.accentTeal)

                        Text(abdomenNotes)
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(TeloscopyTheme.surfaceBackground)
                            .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    }
                }

                // Unrecognized lines
                if let unrecognized = preview.unrecognizedLines, !unrecognized.isEmpty {
                    DisclosureGroup(
                        isExpanded: $showUnrecognizedLines,
                        content: {
                            VStack(alignment: .leading, spacing: 4) {
                                ForEach(unrecognized, id: \.self) { line in
                                    HStack(alignment: .top, spacing: 6) {
                                        Image(systemName: "questionmark.circle")
                                            .font(.caption2)
                                            .foregroundColor(TeloscopyTheme.warningOrange)
                                            .padding(.top, 2)

                                        Text(line)
                                            .font(.caption)
                                            .foregroundColor(TeloscopyTheme.textSecondary)
                                    }
                                    .padding(.vertical, 2)
                                }
                            }
                            .padding(.top, 8)
                        },
                        label: {
                            HStack(spacing: 6) {
                                Image(systemName: "eye.slash")
                                    .font(.caption)

                                Text("\(unrecognized.count) unrecognized lines")
                                    .font(.caption)
                                    .fontWeight(.medium)
                            }
                            .foregroundColor(TeloscopyTheme.warningOrange)
                        }
                    )
                }

                Divider()

                // Proceed button
                Button(action: uploadAndAnalyze) {
                    HStack(spacing: 8) {
                        Image(systemName: "arrow.right.circle.fill")
                        Text("Proceed to Analyse")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(
                        LinearGradient(
                            colors: canAnalyze
                                ? [TeloscopyTheme.primaryBlue, TeloscopyTheme.darkBlue]
                                : [Color.gray.opacity(0.4), Color.gray.opacity(0.3)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .foregroundColor(.white)
                    .cornerRadius(TeloscopyTheme.smallCornerRadius)
                }
                .disabled(!canAnalyze || viewState == .analyzing)
            }
            .padding()
            .cardStyle()
        }
    }

    // MARK: - Health Score Section

    private func healthScoreSection(response: HealthCheckupResponse) -> some View {
        let score = response.overallHealthScore ?? 0
        let totalTested = response.totalTested ?? 0
        let abnormalCount = response.abnormalCount ?? 0
        let normalCount = max(totalTested - abnormalCount, 0)

        return VStack(spacing: 16) {
            HStack {
                Label("Health Score", systemImage: "heart.text.square.fill")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Spacer()
            }

            // Circular arc gauge
            ZStack {
                // Background track
                Circle()
                    .trim(from: 0.0, to: 0.75)
                    .stroke(Color.gray.opacity(0.12), lineWidth: 14)
                    .frame(width: 160, height: 160)
                    .rotationEffect(.degrees(135))

                // Score arc
                Circle()
                    .trim(from: 0.0, to: CGFloat(min(score / 100.0, 1.0)) * 0.75)
                    .stroke(
                        AngularGradient(
                            colors: scoreArcColors,
                            center: .center,
                            startAngle: .degrees(135),
                            endAngle: .degrees(405)
                        ),
                        style: StrokeStyle(lineWidth: 14, lineCap: .round)
                    )
                    .frame(width: 160, height: 160)
                    .rotationEffect(.degrees(135))

                VStack(spacing: 2) {
                    Text("\(Int(score))")
                        .font(.system(size: 42, weight: .bold, design: .rounded))
                        .foregroundColor(scoreColor(score))

                    Text("/ 100")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
            }
            .padding(.vertical, 8)

            // Stats row
            HStack(spacing: 0) {
                statsChip(
                    value: "\(totalTested)",
                    label: "Total Tested",
                    color: TeloscopyTheme.primaryBlue
                )

                Divider()
                    .frame(height: 32)

                statsChip(
                    value: "\(abnormalCount)",
                    label: "Abnormal",
                    color: TeloscopyTheme.warningOrange
                )

                Divider()
                    .frame(height: 32)

                statsChip(
                    value: "\(normalCount)",
                    label: "Normal",
                    color: TeloscopyTheme.successGreen
                )
            }

            // Score breakdown chips
            if let breakdown = response.healthScoreBreakdown, !breakdown.isEmpty {
                let sortedBreakdown = breakdown.sorted { $0.key < $1.key }

                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 10) {
                    ForEach(sortedBreakdown, id: \.key) { key, value in
                        VStack(spacing: 4) {
                            Text(String(format: "%.0f", value))
                                .font(.headline)
                                .fontWeight(.bold)
                                .foregroundColor(scoreColor(value))

                            Text(key.replacingOccurrences(of: "_", with: " ").capitalized)
                                .font(.caption2)
                                .foregroundColor(TeloscopyTheme.textSecondary)
                                .lineLimit(2)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .padding(.horizontal, 4)
                        .background(scoreColor(value).opacity(0.08))
                        .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    }
                }
            }
        }
        .padding()
        .cardStyle()
    }

    private func statsChip(value: String, label: String, color: Color) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(color)

            Text(label)
                .font(.caption2)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Lab Results Section

    private func labResultsSection(response: HealthCheckupResponse) -> some View {
        let labResults = response.labResults ?? []

        return VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("Lab Results", systemImage: "list.clipboard.fill")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Spacer()

                Text("\(labResults.count) parameters")
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }

            if labResults.isEmpty {
                HStack(spacing: 10) {
                    Image(systemName: "doc.text")
                        .font(.title2)
                        .foregroundColor(TeloscopyTheme.textSecondary)

                    Text("No lab results available")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            } else {
                let grouped = Dictionary(grouping: labResults) { $0.category }
                let sortedCategories = grouped.keys.sorted()

                ForEach(sortedCategories, id: \.self) { category in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(category.uppercased())
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(TeloscopyTheme.accentTeal)
                            .tracking(0.8)
                            .padding(.top, 6)

                        if let items = grouped[category] {
                            ForEach(items) { item in
                                labResultRow(item: item)
                            }
                        }

                        if category != sortedCategories.last {
                            Divider()
                                .padding(.vertical, 4)
                        }
                    }
                }
            }
        }
        .padding()
        .cardStyle()
    }

    private func labResultRow(item: LabResultItem) -> some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.displayName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Text("\(String(format: "%.1f", item.referenceLow)) - \(String(format: "%.1f", item.referenceHigh)) \(item.unit)")
                    .font(.caption2)
                    .foregroundColor(TeloscopyTheme.textSecondary)
            }

            Spacer()

            Text(String(format: "%.1f", item.value))
                .font(.subheadline)
                .fontWeight(.bold)
                .foregroundColor(statusColor(item.status))

            Text(item.unit)
                .font(.caption2)
                .foregroundColor(TeloscopyTheme.textSecondary)
                .frame(width: 40, alignment: .leading)

            statusBadge(item.status)
        }
        .padding(.vertical, 6)
        .padding(.horizontal, 10)
        .background(statusColor(item.status).opacity(0.04))
        .cornerRadius(TeloscopyTheme.smallCornerRadius)
    }

    // MARK: - Health Findings Section

    private func healthFindingsSection(response: HealthCheckupResponse) -> some View {
        let findings = response.findings ?? []

        return VStack(alignment: .leading, spacing: 14) {
            Label("Health Findings", systemImage: "stethoscope")
                .font(.headline)
                .foregroundColor(TeloscopyTheme.textPrimary)

            if findings.isEmpty {
                HStack(spacing: 10) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.title2)
                        .foregroundColor(TeloscopyTheme.successGreen)

                    Text("No significant health findings detected")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(TeloscopyTheme.successGreen.opacity(0.05))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
            } else {
                ForEach(findings) { finding in
                    findingCard(finding: finding)
                }
            }
        }
        .padding()
        .cardStyle()
    }

    private func findingCard(finding: HealthFindingItem) -> some View {
        let isExpanded = expandedFindings.contains(finding.condition)

        return VStack(alignment: .leading, spacing: 0) {
            // Header (always visible)
            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    if isExpanded {
                        expandedFindings.remove(finding.condition)
                    } else {
                        expandedFindings.insert(finding.condition)
                    }
                }
            }) {
                HStack(spacing: 10) {
                    Image(systemName: severityIcon(finding.severity))
                        .font(.subheadline)
                        .foregroundColor(severityColor(finding.severity))

                    Text(finding.displayName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(TeloscopyTheme.textPrimary)

                    severityBadge(finding.severity)

                    Spacer()

                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .padding(12)
            }
            .buttonStyle(.plain)

            // Expanded content
            if isExpanded {
                VStack(alignment: .leading, spacing: 12) {
                    // Evidence
                    if !finding.evidence.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Evidence")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.textSecondary)

                            ForEach(finding.evidence, id: \.self) { item in
                                HStack(alignment: .top, spacing: 8) {
                                    Image(systemName: "arrow.right.circle.fill")
                                        .font(.caption2)
                                        .foregroundColor(TeloscopyTheme.primaryBlue)
                                        .padding(.top, 2)

                                    Text(item)
                                        .font(.caption)
                                        .foregroundColor(TeloscopyTheme.textPrimary)
                                }
                            }
                        }
                    }

                    // Dietary impact
                    if !finding.dietaryImpact.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Dietary Impact")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.textSecondary)

                            Text(finding.dietaryImpact)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                                .padding(8)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(TeloscopyTheme.warningOrange.opacity(0.06))
                                .cornerRadius(6)
                        }
                    }

                    // Foods to increase
                    if let foods = finding.foodsToIncrease, !foods.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Foods to Increase", systemImage: "arrow.up.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.successGreen)

                            foodTagsView(items: foods, color: TeloscopyTheme.successGreen)
                        }
                    }

                    // Foods to avoid
                    if let foods = finding.foodsToAvoid, !foods.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Foods to Avoid", systemImage: "arrow.down.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.errorRed)

                            foodTagsView(items: foods, color: TeloscopyTheme.errorRed)
                        }
                    }

                    // Nutrients to increase
                    if let nutrients = finding.nutrientsToIncrease, !nutrients.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Nutrients to Increase", systemImage: "plus.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.accentTeal)

                            foodTagsView(items: nutrients, color: TeloscopyTheme.accentTeal)
                        }
                    }

                    // Nutrients to decrease
                    if let nutrients = finding.nutrientsToDecrease, !nutrients.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Nutrients to Decrease", systemImage: "minus.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.warningOrange)

                            foodTagsView(items: nutrients, color: TeloscopyTheme.warningOrange)
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(severityColor(finding.severity).opacity(0.04))
        .cornerRadius(TeloscopyTheme.smallCornerRadius)
        .overlay(
            RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                .stroke(severityColor(finding.severity).opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - Abdomen Findings Section

    private func abdomenFindingsSection(response: HealthCheckupResponse) -> some View {
        let abdomenFindings = response.abdomenFindings ?? []

        return Group {
            if !abdomenFindings.isEmpty {
                VStack(alignment: .leading, spacing: 14) {
                    Label("Abdomen Findings", systemImage: "figure.stand")
                        .font(.headline)
                        .foregroundColor(TeloscopyTheme.textPrimary)

                    ForEach(abdomenFindings) { finding in
                        abdomenFindingCard(finding: finding)
                    }
                }
                .padding()
                .cardStyle()
            }
        }
    }

    private func abdomenFindingCard(finding: AbdomenFindingItem) -> some View {
        let identifier = "\(finding.organ)-\(finding.finding)"
        let isExpanded = expandedAbdomenFindings.contains(identifier)

        return VStack(alignment: .leading, spacing: 0) {
            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    if isExpanded {
                        expandedAbdomenFindings.remove(identifier)
                    } else {
                        expandedAbdomenFindings.insert(identifier)
                    }
                }
            }) {
                HStack(spacing: 10) {
                    Image(systemName: "cross.case.fill")
                        .font(.subheadline)
                        .foregroundColor(severityColor(finding.severity))

                    VStack(alignment: .leading, spacing: 2) {
                        Text(finding.organ)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.textPrimary)

                        Text(finding.finding)
                            .font(.caption)
                            .foregroundColor(TeloscopyTheme.textSecondary)
                    }

                    Spacer()

                    severityBadge(finding.severity)

                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .padding(12)
            }
            .buttonStyle(.plain)

            if isExpanded {
                VStack(alignment: .leading, spacing: 12) {
                    // Dietary impact
                    if !finding.dietaryImpact.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Dietary Impact")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.textSecondary)

                            Text(finding.dietaryImpact)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                                .padding(8)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(TeloscopyTheme.warningOrange.opacity(0.06))
                                .cornerRadius(6)
                        }
                    }

                    if let foods = finding.foodsToIncrease, !foods.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Foods to Increase", systemImage: "arrow.up.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.successGreen)

                            foodTagsView(items: foods, color: TeloscopyTheme.successGreen)
                        }
                    }

                    if let foods = finding.foodsToAvoid, !foods.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Foods to Avoid", systemImage: "arrow.down.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.errorRed)

                            foodTagsView(items: foods, color: TeloscopyTheme.errorRed)
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 12)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(severityColor(finding.severity).opacity(0.04))
        .cornerRadius(TeloscopyTheme.smallCornerRadius)
        .overlay(
            RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                .stroke(severityColor(finding.severity).opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - Detected Conditions Section

    private func detectedConditionsSection(response: HealthCheckupResponse) -> some View {
        let conditions = response.detectedConditions ?? []

        return VStack(alignment: .leading, spacing: 14) {
            Label("Detected Conditions", systemImage: "tag.fill")
                .font(.headline)
                .foregroundColor(TeloscopyTheme.textPrimary)

            if conditions.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(TeloscopyTheme.successGreen)

                    Text("No conditions detected")
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .padding()
            } else {
                FlowLayout(spacing: 8) {
                    ForEach(conditions, id: \.self) { condition in
                        HStack(spacing: 4) {
                            Image(systemName: "exclamationmark.circle.fill")
                                .font(.system(size: 10))
                            Text(condition)
                        }
                        .font(.caption)
                        .fontWeight(.medium)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 7)
                        .background(TeloscopyTheme.warningOrange.opacity(0.12))
                        .foregroundColor(TeloscopyTheme.warningOrange)
                        .cornerRadius(16)
                    }
                }
            }
        }
        .padding()
        .cardStyle()
    }

    // MARK: - Diet Recommendation Section

    private func dietRecommendationSection(diet: DietRecommendation) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("Diet Recommendation", systemImage: "leaf.fill")
                    .font(.headline)
                    .foregroundColor(TeloscopyTheme.textPrimary)

                Spacer()

                Text("\(diet.displayCalories) kcal/day")
                    .font(.caption)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(TeloscopyTheme.accentTeal.opacity(0.15))
                    .foregroundColor(TeloscopyTheme.accentTeal)
                    .cornerRadius(8)
            }

            VStack(alignment: .leading, spacing: 16) {
                // Summary
                if let summary = diet.summary, !summary.isEmpty {
                    Text(summary)
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textPrimary)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(TeloscopyTheme.primaryBlue.opacity(0.05))
                        .cornerRadius(TeloscopyTheme.smallCornerRadius)
                }

                // Key nutrients
                let nutrients = diet.displayNutrients
                if !nutrients.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Key Nutrients", systemImage: "pill.fill")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.accentTeal)

                        FlowLayout(spacing: 6) {
                            ForEach(nutrients, id: \.self) { nutrient in
                                HStack(spacing: 4) {
                                    Image(systemName: "star.fill")
                                        .font(.system(size: 8))
                                    Text(nutrient)
                                }
                                .font(.caption)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .background(TeloscopyTheme.accentTeal.opacity(0.1))
                                .foregroundColor(TeloscopyTheme.accentTeal)
                                .cornerRadius(12)
                            }
                        }
                    }
                }

                Divider()

                // Foods to increase
                let targetFoods = diet.displayTargetFoods
                if !targetFoods.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Foods to Increase", systemImage: "plus.circle.fill")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.successGreen)

                        foodTagsView(items: targetFoods, color: TeloscopyTheme.successGreen)
                    }
                }

                // Foods to avoid
                let avoidFoods = diet.displayAvoidFoods
                if !avoidFoods.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Foods to Avoid", systemImage: "minus.circle.fill")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.errorRed)

                        foodTagsView(items: avoidFoods, color: TeloscopyTheme.errorRed)
                    }
                }

                // Meal plans
                if let mealPlans = diet.mealPlans, !mealPlans.isEmpty {
                    Divider()

                    VStack(alignment: .leading, spacing: 8) {
                        Label("Meal Plans", systemImage: "fork.knife.circle.fill")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(TeloscopyTheme.primaryBlue)

                        ForEach(mealPlans) { plan in
                            mealPlanCard(plan: plan)
                        }
                    }
                }
            }
        }
        .padding()
        .cardStyle()
    }

    private func mealPlanCard(plan: MealPlan) -> some View {
        let dayKey = "day-\(plan.day)"
        let isExpanded = expandedMealPlans.contains(dayKey)

        return VStack(alignment: .leading, spacing: 0) {
            Button(action: {
                withAnimation(.spring(response: 0.3)) {
                    if isExpanded {
                        expandedMealPlans.remove(dayKey)
                    } else {
                        expandedMealPlans.insert(dayKey)
                    }
                }
            }) {
                HStack {
                    Image(systemName: "calendar.circle.fill")
                        .foregroundColor(TeloscopyTheme.primaryBlue)

                    Text("Day \(plan.day)")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(TeloscopyTheme.textPrimary)

                    Spacer()

                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }
                .padding(10)
            }
            .buttonStyle(.plain)

            if isExpanded {
                VStack(alignment: .leading, spacing: 10) {
                    mealRow(
                        icon: "sunrise.fill",
                        label: "Breakfast",
                        items: plan.breakfast,
                        color: TeloscopyTheme.warningOrange
                    )
                    mealRow(
                        icon: "sun.max.fill",
                        label: "Lunch",
                        items: plan.lunch,
                        color: TeloscopyTheme.primaryBlue
                    )
                    mealRow(
                        icon: "moon.fill",
                        label: "Dinner",
                        items: plan.dinner,
                        color: TeloscopyTheme.darkBlue
                    )

                    if !plan.snacks.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Label("Snacks", systemImage: "leaf.circle.fill")
                                .font(.caption)
                                .fontWeight(.bold)
                                .foregroundColor(TeloscopyTheme.successGreen)

                            ForEach(plan.snacks, id: \.self) { snack in
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(TeloscopyTheme.successGreen)
                                        .frame(width: 4, height: 4)

                                    Text(snack)
                                        .font(.caption)
                                        .foregroundColor(TeloscopyTheme.textPrimary)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, 10)
                .padding(.bottom, 10)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(TeloscopyTheme.surfaceBackground)
        .cornerRadius(TeloscopyTheme.smallCornerRadius)
    }

    private func mealRow(icon: String, label: String, items: [String], color: Color) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(color)
                .frame(width: 16)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(TeloscopyTheme.textSecondary)

                Text(items.joined(separator: ", "))
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textPrimary)
            }
        }
    }

    // MARK: - Dietary Modifications Section

    private func dietaryModificationsSection(response: HealthCheckupResponse) -> some View {
        let modifications = response.dietaryModifications ?? []

        return Group {
            if !modifications.isEmpty {
                VStack(alignment: .leading, spacing: 14) {
                    Label("Dietary Modifications", systemImage: "list.number")
                        .font(.headline)
                        .foregroundColor(TeloscopyTheme.textPrimary)

                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(modifications.enumerated()), id: \.offset) { index, modification in
                            HStack(alignment: .top, spacing: 10) {
                                Text("\(index + 1)")
                                    .font(.caption)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)
                                    .frame(width: 22, height: 22)
                                    .background(TeloscopyTheme.primaryBlue)
                                    .clipShape(Circle())

                                Text(modification)
                                    .font(.subheadline)
                                    .foregroundColor(TeloscopyTheme.textPrimary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .padding(.vertical, 4)

                            if index < modifications.count - 1 {
                                Divider()
                                    .padding(.leading, 32)
                            }
                        }
                    }

                    if let adjustment = response.calorieAdjustment, adjustment != 0 {
                        HStack(spacing: 8) {
                            Image(systemName: adjustment > 0 ? "arrow.up.right" : "arrow.down.right")
                                .font(.caption)
                                .foregroundColor(adjustment > 0 ? TeloscopyTheme.warningOrange : TeloscopyTheme.successGreen)

                            Text("Calorie adjustment: \(adjustment > 0 ? "+" : "")\(adjustment) kcal/day")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(TeloscopyTheme.primaryBlue.opacity(0.06))
                        .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    }
                }
                .padding()
                .cardStyle()
            }
        }
    }

    // MARK: - Ayurvedic Analysis Section

    private func ayurvedicAnalysisSection(ayurvedic: AyurvedicAnalysis) -> some View {
        let amberColor = Color(hex: 0xD97706)

        return VStack(alignment: .leading, spacing: 16) {
            // Header
            HStack(spacing: 10) {
                ZStack {
                    Circle()
                        .fill(amberColor.opacity(0.15))
                        .frame(width: 40, height: 40)
                    Image(systemName: "leaf.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(amberColor)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Ayurvedic Analysis")
                        .font(.headline)
                        .foregroundColor(TeloscopyTheme.textPrimary)
                    Text("Traditional Indian Medicine Insights")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }

                Spacer()
            }

            // Dosha Assessment
            if !ayurvedic.doshaAssessment.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Dosha Assessment", systemImage: "circle.hexagongrid.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(amberColor)

                    Text(ayurvedic.doshaAssessment)
                        .font(.subheadline)
                        .foregroundColor(TeloscopyTheme.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(amberColor.opacity(0.06))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
                .overlay(
                    RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                        .stroke(amberColor.opacity(0.2), lineWidth: 1)
                )
            }

            // Remedies
            if !ayurvedic.remedies.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Label("Remedies", systemImage: "cross.vial.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(amberColor)

                    ForEach(Array(ayurvedic.remedies.enumerated()), id: \.offset) { _, remedy in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(remedy.name)
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(TeloscopyTheme.textPrimary)

                                Spacer()

                                if !remedy.source.isEmpty {
                                    Text(remedy.source)
                                        .font(.caption2)
                                        .fontWeight(.bold)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 3)
                                        .background(amberColor.opacity(0.15))
                                        .foregroundColor(amberColor)
                                        .cornerRadius(6)
                                }
                            }

                            if !remedy.ingredients.isEmpty {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Ingredients")
                                        .font(.caption)
                                        .fontWeight(.medium)
                                        .foregroundColor(TeloscopyTheme.textSecondary)
                                    FlowLayout(spacing: 6) {
                                        ForEach(remedy.ingredients, id: \.self) { ingredient in
                                            Text(ingredient)
                                                .font(.caption)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 4)
                                                .background(amberColor.opacity(0.08))
                                                .foregroundColor(amberColor)
                                                .cornerRadius(10)
                                        }
                                    }
                                }
                            }

                            if !remedy.preparation.isEmpty {
                                ayurvedicDetailRow(label: "Preparation", value: remedy.preparation, color: amberColor)
                            }

                            if !remedy.dosage.isEmpty {
                                ayurvedicDetailRow(label: "Dosage", value: remedy.dosage, color: amberColor)
                            }

                            if !remedy.mechanism.isEmpty {
                                ayurvedicDetailRow(label: "Mechanism", value: remedy.mechanism, color: amberColor)
                            }

                            if !remedy.forConditions.isEmpty {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("For Conditions")
                                        .font(.caption)
                                        .fontWeight(.medium)
                                        .foregroundColor(TeloscopyTheme.textSecondary)
                                    FlowLayout(spacing: 6) {
                                        ForEach(remedy.forConditions, id: \.self) { condition in
                                            Text(condition)
                                                .font(.caption)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 4)
                                                .background(TeloscopyTheme.primaryBlue.opacity(0.08))
                                                .foregroundColor(TeloscopyTheme.primaryBlue)
                                                .cornerRadius(10)
                                        }
                                    }
                                }
                            }
                        }
                        .padding()
                        .background(TeloscopyTheme.surfaceBackground)
                        .cornerRadius(TeloscopyTheme.smallCornerRadius)
                    }
                }
            }

            // Yoga Asanas & Pranayama
            if !ayurvedic.yogaAsanas.isEmpty || !ayurvedic.pranayama.isEmpty {
                HStack(alignment: .top, spacing: 12) {
                    if !ayurvedic.yogaAsanas.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("Yoga Asanas", systemImage: "figure.mind.and.body")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(amberColor)

                            ForEach(ayurvedic.yogaAsanas, id: \.self) { asana in
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(amberColor)
                                        .frame(width: 5, height: 5)
                                    Text(asana)
                                        .font(.caption)
                                        .foregroundColor(TeloscopyTheme.textPrimary)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if !ayurvedic.pranayama.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("Pranayama", systemImage: "wind")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(amberColor)

                            ForEach(ayurvedic.pranayama, id: \.self) { technique in
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(amberColor)
                                        .frame(width: 5, height: 5)
                                    Text(technique)
                                        .font(.caption)
                                        .foregroundColor(TeloscopyTheme.textPrimary)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding()
                .background(amberColor.opacity(0.04))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
            }

            // Lifestyle Recommendations
            if !ayurvedic.lifestyleRecommendations.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Lifestyle Recommendations", systemImage: "heart.text.square.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(amberColor)

                    ForEach(Array(ayurvedic.lifestyleRecommendations.enumerated()), id: \.offset) { index, rec in
                        HStack(alignment: .top, spacing: 8) {
                            Text("\(index + 1)")
                                .font(.caption2)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                                .frame(width: 20, height: 20)
                                .background(amberColor)
                                .clipShape(Circle())
                            Text(rec)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }

            // Dietary Principles
            if !ayurvedic.dietaryPrinciples.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Dietary Principles", systemImage: "fork.knife.circle.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(amberColor)

                    FlowLayout(spacing: 6) {
                        ForEach(ayurvedic.dietaryPrinciples, id: \.self) { principle in
                            Text(principle)
                                .font(.caption)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .background(amberColor.opacity(0.1))
                                .foregroundColor(amberColor)
                                .cornerRadius(12)
                        }
                    }
                }
            }

            // Contraindications
            if !ayurvedic.contraindications.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Contraindications", systemImage: "exclamationmark.triangle.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(TeloscopyTheme.errorRed)

                    ForEach(ayurvedic.contraindications, id: \.self) { item in
                        HStack(alignment: .top, spacing: 8) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.errorRed)
                            Text(item)
                                .font(.caption)
                                .foregroundColor(TeloscopyTheme.textPrimary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding()
                .background(TeloscopyTheme.errorRed.opacity(0.06))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
                .overlay(
                    RoundedRectangle(cornerRadius: TeloscopyTheme.smallCornerRadius)
                        .stroke(TeloscopyTheme.errorRed.opacity(0.2), lineWidth: 1)
                )
            }

            // Ayurvedic Disclaimer
            if !ayurvedic.disclaimer.isEmpty {
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "info.circle.fill")
                        .font(.caption)
                        .foregroundColor(amberColor)
                    Text(ayurvedic.disclaimer)
                        .font(.caption2)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(10)
                .background(amberColor.opacity(0.04))
                .cornerRadius(TeloscopyTheme.smallCornerRadius)
            }
        }
        .padding()
        .cardStyle()
    }

    private func ayurvedicDetailRow(label: String, value: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(TeloscopyTheme.textSecondary)
            Text(value)
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - LLM Analysis Section

    private func llmAnalysisSection(text: String) -> some View {
        let purpleColor = Color(hex: 0x8B5CF6)

        return VStack(alignment: .leading, spacing: 14) {
            // Header
            HStack(spacing: 10) {
                ZStack {
                    Circle()
                        .fill(purpleColor.opacity(0.15))
                        .frame(width: 40, height: 40)
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 20))
                        .foregroundColor(purpleColor)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("AI-Powered Integrated Analysis")
                        .font(.headline)
                        .foregroundColor(TeloscopyTheme.textPrimary)
                    Text("Modern Medicine + Ayurvedic Wisdom")
                        .font(.caption)
                        .foregroundColor(TeloscopyTheme.textSecondary)
                }

                Spacer()
            }

            // Rendered markdown-like content
            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(text.components(separatedBy: "\n").enumerated()), id: \.offset) { _, line in
                    parsedMarkdownLine(line, accentColor: purpleColor)
                }
            }
        }
        .padding()
        .cardStyle()
    }

    @ViewBuilder
    private func parsedMarkdownLine(_ line: String, accentColor: Color) -> some View {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        if trimmed.isEmpty {
            Spacer().frame(height: 4)
        } else if trimmed.hasPrefix("## ") {
            Text(trimmed.replacingOccurrences(of: "## ", with: ""))
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(accentColor)
                .padding(.top, 6)
        } else if trimmed.hasPrefix("### ") {
            Text(trimmed.replacingOccurrences(of: "### ", with: ""))
                .font(.subheadline)
                .fontWeight(.bold)
                .foregroundColor(TeloscopyTheme.textPrimary)
                .padding(.top, 4)
        } else if trimmed.hasPrefix("- ") {
            HStack(alignment: .top, spacing: 8) {
                Circle()
                    .fill(accentColor)
                    .frame(width: 5, height: 5)
                    .padding(.top, 6)
                styledInlineText(String(trimmed.dropFirst(2)))
                    .font(.subheadline)
                    .foregroundColor(TeloscopyTheme.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        } else {
            styledInlineText(trimmed)
                .font(.subheadline)
                .foregroundColor(TeloscopyTheme.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func styledInlineText(_ input: String) -> Text {
        var result = Text("")
        var remaining = input[input.startIndex...]

        while !remaining.isEmpty {
            if let boldRange = remaining.range(of: "**") {
                // Text before the bold marker
                let before = remaining[remaining.startIndex..<boldRange.lowerBound]
                if !before.isEmpty {
                    result = result + Text(parseItalic(String(before)))
                }
                let afterOpen = remaining[boldRange.upperBound...]
                if let closeRange = afterOpen.range(of: "**") {
                    let boldText = afterOpen[afterOpen.startIndex..<closeRange.lowerBound]
                    result = result + Text(String(boldText)).bold()
                    remaining = afterOpen[closeRange.upperBound...]
                } else {
                    // No closing **, just output the rest
                    result = result + Text(parseItalic(String(remaining)))
                    break
                }
            } else {
                result = result + Text(parseItalic(String(remaining)))
                break
            }
        }
        return result
    }

    private func parseItalic(_ input: String) -> AttributedString {
        var attrStr = AttributedString(input)
        // Simple italic handling: replace *text* with italic
        guard let startIdx = input.firstIndex(of: "*") else {
            return attrStr
        }
        let afterStart = input.index(after: startIdx)
        guard afterStart < input.endIndex,
              let endIdx = input[afterStart...].firstIndex(of: "*") else {
            return attrStr
        }
        // Reconstruct with italic attribute
        let prefix = String(input[input.startIndex..<startIdx])
        let italicPart = String(input[afterStart..<endIdx])
        let suffix = String(input[input.index(after: endIdx)...])
        var result = AttributedString(prefix)
        var italicAttr = AttributedString(italicPart)
        italicAttr.font = .subheadline.italic()
        result.append(italicAttr)
        result.append(AttributedString(suffix))
        return result
    }

    // MARK: - Disclaimer Section

    private func disclaimerSection(text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.shield.fill")
                .font(.title3)
                .foregroundColor(TeloscopyTheme.warningOrange)

            VStack(alignment: .leading, spacing: 4) {
                Text("Disclaimer")
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(TeloscopyTheme.warningOrange)

                Text(text)
                    .font(.caption)
                    .foregroundColor(TeloscopyTheme.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding()
        .background(TeloscopyTheme.warningOrange.opacity(0.06))
        .cornerRadius(TeloscopyTheme.cornerRadius)
        .overlay(
            RoundedRectangle(cornerRadius: TeloscopyTheme.cornerRadius)
                .stroke(TeloscopyTheme.warningOrange.opacity(0.2), lineWidth: 1)
        )
        .padding(.bottom, 20)
    }

    // MARK: - Reusable Components

    private func confidenceBadge(_ confidence: Double) -> some View {
        let percentage = confidence * 100
        let color: Color = confidence >= 0.7
            ? TeloscopyTheme.successGreen
            : confidence >= 0.4
                ? TeloscopyTheme.warningOrange
                : TeloscopyTheme.errorRed

        return Text(String(format: "%.0f%% confidence", percentage))
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(color.opacity(0.15))
            .foregroundColor(color)
            .cornerRadius(10)
    }

    private func extractionCountChip(count: Int, label: String, color: Color) -> some View {
        HStack(spacing: 4) {
            Text("\(count)")
                .font(.subheadline)
                .fontWeight(.bold)
                .foregroundColor(color)

            Text(label)
                .font(.caption)
                .foregroundColor(TeloscopyTheme.textSecondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(color.opacity(0.08))
        .cornerRadius(8)
    }

    private func statusBadge(_ status: String) -> some View {
        Text(status.replacingOccurrences(of: "_", with: " ").capitalized)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(statusColor(status).opacity(0.15))
            .foregroundColor(statusColor(status))
            .cornerRadius(6)
    }

    private func severityBadge(_ severity: String) -> some View {
        Text(severity.capitalized)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(severityColor(severity).opacity(0.15))
            .foregroundColor(severityColor(severity))
            .cornerRadius(6)
    }

    private func foodTagsView(items: [String], color: Color) -> some View {
        FlowLayout(spacing: 6) {
            ForEach(items, id: \.self) { item in
                Text(item)
                    .font(.caption)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(color.opacity(0.1))
                    .foregroundColor(color)
                    .cornerRadius(12)
            }
        }
    }

    // MARK: - Color Helpers

    private func statusColor(_ status: String) -> Color {
        switch status.lowercased() {
        case "normal":
            return TeloscopyTheme.successGreen
        case "high", "low":
            return TeloscopyTheme.warningOrange
        case "critical", "critical_high", "critical_low":
            return TeloscopyTheme.errorRed
        default:
            return TeloscopyTheme.textSecondary
        }
    }

    private func severityColor(_ severity: String) -> Color {
        switch severity.lowercased() {
        case "mild":
            return TeloscopyTheme.warningOrange
        case "moderate":
            return Color(red: 0.9, green: 0.45, blue: 0.1)
        case "severe":
            return TeloscopyTheme.errorRed
        default:
            return TeloscopyTheme.textSecondary
        }
    }

    private func severityIcon(_ severity: String) -> String {
        switch severity.lowercased() {
        case "mild":
            return "exclamationmark.circle"
        case "moderate":
            return "exclamationmark.triangle"
        case "severe":
            return "exclamationmark.octagon.fill"
        default:
            return "info.circle"
        }
    }

    private func scoreColor(_ score: Double) -> Color {
        if score >= 75 { return TeloscopyTheme.successGreen }
        if score >= 60 { return TeloscopyTheme.accentTeal }
        if score >= 40 { return TeloscopyTheme.warningOrange }
        return TeloscopyTheme.errorRed
    }

    private var scoreArcColors: [Color] {
        [
            TeloscopyTheme.errorRed,
            TeloscopyTheme.warningOrange,
            Color.yellow,
            TeloscopyTheme.successGreen
        ]
    }

    private func scoreGradientColors(_ score: Double) -> [Color] {
        if score >= 75 { return [TeloscopyTheme.successGreen, TeloscopyTheme.accentTeal] }
        if score >= 60 { return [TeloscopyTheme.accentTeal, TeloscopyTheme.primaryBlue] }
        if score >= 40 { return [TeloscopyTheme.warningOrange, TeloscopyTheme.accentTeal] }
        return [TeloscopyTheme.errorRed, TeloscopyTheme.warningOrange]
    }

    private func fileIcon(for fileName: String) -> String {
        let ext = (fileName as NSString).pathExtension.lowercased()
        switch ext {
        case "pdf":
            return "doc.richtext"
        case "png", "jpg", "jpeg":
            return "photo"
        case "txt":
            return "doc.plaintext"
        default:
            return "doc"
        }
    }

    // MARK: - File Handling

    private func handleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            guard url.startAccessingSecurityScopedResource() else {
                viewState = .error("Unable to access the selected file. Please try again.")
                return
            }
            defer { url.stopAccessingSecurityScopedResource() }

            do {
                let data = try Data(contentsOf: url)
                selectedFileData = data
                selectedFileName = url.lastPathComponent
                selectedFileSize = data.count

                // Clear previous results
                parsePreview = nil
                checkupResponse = nil
                viewState = .idle
            } catch {
                viewState = .error("Failed to read file: \(error.localizedDescription)")
            }

        case .failure(let error):
            viewState = .error("File selection failed: \(error.localizedDescription)")
        }
    }

    private func clearFile() {
        withAnimation {
            selectedFileData = nil
            selectedFileName = ""
            selectedFileSize = 0
            parsePreview = nil
            checkupResponse = nil
            viewState = .idle
        }
    }

    private func formattedFileSize(_ bytes: Int) -> String {
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useKB, .useMB]
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(bytes))
    }

    // MARK: - Network Requests

    private func extractValues() {
        guard let fileData = selectedFileData else { return }

        viewState = .parsing
        parsePreview = nil

        Task {
            do {
                let preview = try await apiService.parseHealthReport(
                    fileData: fileData,
                    fileName: selectedFileName
                )
                await MainActor.run {
                    parsePreview = preview
                    viewState = .parsed
                }
            } catch {
                await MainActor.run {
                    viewState = .error("Failed to extract values: \(error.localizedDescription)")
                }
            }
        }
    }

    private func uploadAndAnalyze() {
        guard let fileData = selectedFileData,
              let ageInt = Int(age), ageInt > 0 else {
            viewState = .error("Please fill in all profile fields with valid values.")
            return
        }

        viewState = .analyzing
        checkupResponse = nil

        Task {
            do {
                let response = try await apiService.uploadHealthReport(
                    fileData: fileData,
                    fileName: selectedFileName,
                    age: ageInt,
                    sex: sex,
                    region: region
                )
                await MainActor.run {
                    checkupResponse = response
                    parsePreview = nil
                    viewState = .results
                }
            } catch {
                await MainActor.run {
                    viewState = .error("Analysis failed: \(error.localizedDescription)")
                }
            }
        }
    }

    private func retryLastAction() {
        if parsePreview != nil || checkupResponse != nil {
            uploadAndAnalyze()
        } else {
            extractValues()
        }
    }

    private func dismissError() {
        if checkupResponse != nil {
            viewState = .results
        } else if parsePreview != nil {
            viewState = .parsed
        } else {
            viewState = .idle
        }
    }
}

// MARK: - Flow Layout (for tag-like chips)

private struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = arrange(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = arrange(proposal: proposal, subviews: subviews)

        for (index, position) in result.positions.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y),
                proposal: ProposedViewSize(subviews[index].sizeThatFits(.unspecified))
            )
        }
    }

    private struct ArrangeResult {
        var size: CGSize
        var positions: [CGPoint]
    }

    private func arrange(proposal: ProposedViewSize, subviews: Subviews) -> ArrangeResult {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var currentX: CGFloat = 0
        var currentY: CGFloat = 0
        var lineHeight: CGFloat = 0
        var totalWidth: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)

            if currentX + size.width > maxWidth && currentX > 0 {
                currentX = 0
                currentY += lineHeight + spacing
                lineHeight = 0
            }

            positions.append(CGPoint(x: currentX, y: currentY))
            lineHeight = max(lineHeight, size.height)
            currentX += size.width + spacing
            totalWidth = max(totalWidth, currentX - spacing)
        }

        let totalHeight = currentY + lineHeight
        return ArrangeResult(
            size: CGSize(width: totalWidth, height: totalHeight),
            positions: positions
        )
    }
}

// MARK: - Preview

#Preview {
    NavigationStack {
        HealthCheckupView()
    }
    .environmentObject(APIService.shared)
}
