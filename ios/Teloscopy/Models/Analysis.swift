// Analysis.swift
// Teloscopy
//
// Data models for genomic telomere analysis
//

import Foundation
import SwiftUI

// MARK: - Analysis Status

enum AnalysisStatus: String, Codable, CaseIterable {
    case pending = "pending"
    case uploading = "uploading"
    case processing = "processing"
    case completed = "completed"
    case failed = "failed"
    
    var displayName: String {
        switch self {
        case .pending: return "Pending"
        case .uploading: return "Uploading"
        case .processing: return "Processing"
        case .completed: return "Completed"
        case .failed: return "Failed"
        }
    }
    
    var iconName: String {
        switch self {
        case .pending: return "clock"
        case .uploading: return "arrow.up.circle"
        case .processing: return "gearshape.2"
        case .completed: return "checkmark.circle.fill"
        case .failed: return "exclamationmark.triangle.fill"
        }
    }
    
    var color: Color {
        switch self {
        case .pending: return .gray
        case .uploading: return .blue
        case .processing: return .orange
        case .completed: return .green
        case .failed: return .red
        }
    }
}

// MARK: - Analysis Type

enum AnalysisType: String, Codable, CaseIterable, Identifiable {
    case telomereLength = "telomere_length"
    case chromosomeAberration = "chromosome_aberration"
    case fluorescenceIntensity = "fluorescence_intensity"
    case qFISH = "q_fish"
    case flowFISH = "flow_fish"
    
    var id: String { rawValue }
    
    var displayName: String {
        switch self {
        case .telomereLength: return "Telomere Length"
        case .chromosomeAberration: return "Chromosome Aberration"
        case .fluorescenceIntensity: return "Fluorescence Intensity"
        case .qFISH: return "Q-FISH Analysis"
        case .flowFISH: return "Flow-FISH Analysis"
        }
    }
    
    var description: String {
        switch self {
        case .telomereLength:
            return "Measure telomere lengths across all chromosomes using quantitative image analysis."
        case .chromosomeAberration:
            return "Detect structural and numerical chromosome aberrations related to telomere dysfunction."
        case .fluorescenceIntensity:
            return "Quantify fluorescence signal intensity for telomere-specific probes."
        case .qFISH:
            return "Quantitative fluorescence in situ hybridization for individual telomere measurement."
        case .flowFISH:
            return "Flow cytometry-based FISH for high-throughput telomere length distribution analysis."
        }
    }
    
    var iconName: String {
        switch self {
        case .telomereLength: return "ruler"
        case .chromosomeAberration: return "exclamationmark.triangle"
        case .fluorescenceIntensity: return "light.max"
        case .qFISH: return "microscope"
        case .flowFISH: return "waveform.path.ecg"
        }
    }
}

// MARK: - Chromosome Data

struct ChromosomeData: Codable, Identifiable, Hashable {
    let id: UUID
    let chromosomeNumber: Int
    let pArmLength: Double
    let qArmLength: Double
    let averageLength: Double
    let fluorescenceIntensity: Double
    let aberrationDetected: Bool
    let aberrationType: String?
    let confidenceScore: Double
    
    var displayName: String {
        if chromosomeNumber == 23 { return "X" }
        else if chromosomeNumber == 24 { return "Y" }
        return "\(chromosomeNumber)"
    }
    
    var totalLength: Double { pArmLength + qArmLength }
    
    var lengthCategory: LengthCategory {
        if averageLength < 4.0 { return .short }
        else if averageLength < 8.0 { return .medium }
        else { return .long }
    }
    
    enum LengthCategory: String {
        case short = "Short"
        case medium = "Medium"
        case long = "Long"
        
        var color: Color {
            switch self {
            case .short: return .red
            case .medium: return .orange
            case .long: return .green
            }
        }
    }
    
    enum CodingKeys: String, CodingKey {
        case id
        case chromosomeNumber = "chromosome_number"
        case pArmLength = "p_arm_length"
        case qArmLength = "q_arm_length"
        case averageLength = "average_length"
        case fluorescenceIntensity = "fluorescence_intensity"
        case aberrationDetected = "aberration_detected"
        case aberrationType = "aberration_type"
        case confidenceScore = "confidence_score"
    }
    
    init(
        id: UUID = UUID(),
        chromosomeNumber: Int,
        pArmLength: Double,
        qArmLength: Double,
        averageLength: Double,
        fluorescenceIntensity: Double,
        aberrationDetected: Bool = false,
        aberrationType: String? = nil,
        confidenceScore: Double = 0.95
    ) {
        self.id = id
        self.chromosomeNumber = chromosomeNumber
        self.pArmLength = pArmLength
        self.qArmLength = qArmLength
        self.averageLength = averageLength
        self.fluorescenceIntensity = fluorescenceIntensity
        self.aberrationDetected = aberrationDetected
        self.aberrationType = aberrationType
        self.confidenceScore = confidenceScore
    }
}

// MARK: - Telomere Result

struct TelomereResult: Codable, Identifiable {
    let id: UUID
    let meanTelomereLength: Double
    let medianTelomereLength: Double
    let standardDeviation: Double
    let shortestTelomere: Double
    let longestTelomere: Double
    let percentileTenth: Double
    let percentileNinetieth: Double
    let totalCellsAnalyzed: Int
    let qualityScore: Double
    let chromosomeData: [ChromosomeData]
    let ageEstimate: Double?
    let biologicalAgeOffset: Double?
    let telomereDistribution: [DistributionBin]
    
    var healthIndicator: HealthIndicator {
        if meanTelomereLength < 4.0 { return .critical }
        else if meanTelomereLength < 6.0 { return .warning }
        else if meanTelomereLength < 9.0 { return .normal }
        else { return .excellent }
    }
    
    enum HealthIndicator: String {
        case critical = "Critical"
        case warning = "Below Average"
        case normal = "Normal"
        case excellent = "Excellent"
        
        var color: Color {
            switch self {
            case .critical: return .red
            case .warning: return .orange
            case .normal: return .blue
            case .excellent: return .green
            }
        }
        
        var iconName: String {
            switch self {
            case .critical: return "exclamationmark.octagon.fill"
            case .warning: return "exclamationmark.triangle.fill"
            case .normal: return "checkmark.circle.fill"
            case .excellent: return "star.circle.fill"
            }
        }
    }
    
    enum CodingKeys: String, CodingKey {
        case id
        case meanTelomereLength = "mean_telomere_length"
        case medianTelomereLength = "median_telomere_length"
        case standardDeviation = "standard_deviation"
        case shortestTelomere = "shortest_telomere"
        case longestTelomere = "longest_telomere"
        case percentileTenth = "percentile_10th"
        case percentileNinetieth = "percentile_90th"
        case totalCellsAnalyzed = "total_cells_analyzed"
        case qualityScore = "quality_score"
        case chromosomeData = "chromosome_data"
        case ageEstimate = "age_estimate"
        case biologicalAgeOffset = "biological_age_offset"
        case telomereDistribution = "telomere_distribution"
    }
    
    init(
        id: UUID = UUID(),
        meanTelomereLength: Double,
        medianTelomereLength: Double,
        standardDeviation: Double,
        shortestTelomere: Double,
        longestTelomere: Double,
        percentileTenth: Double,
        percentileNinetieth: Double,
        totalCellsAnalyzed: Int,
        qualityScore: Double,
        chromosomeData: [ChromosomeData],
        ageEstimate: Double? = nil,
        biologicalAgeOffset: Double? = nil,
        telomereDistribution: [DistributionBin] = []
    ) {
        self.id = id
        self.meanTelomereLength = meanTelomereLength
        self.medianTelomereLength = medianTelomereLength
        self.standardDeviation = standardDeviation
        self.shortestTelomere = shortestTelomere
        self.longestTelomere = longestTelomere
        self.percentileTenth = percentileTenth
        self.percentileNinetieth = percentileNinetieth
        self.totalCellsAnalyzed = totalCellsAnalyzed
        self.qualityScore = qualityScore
        self.chromosomeData = chromosomeData
        self.ageEstimate = ageEstimate
        self.biologicalAgeOffset = biologicalAgeOffset
        self.telomereDistribution = telomereDistribution
    }
}

// MARK: - Distribution Bin

struct DistributionBin: Codable, Identifiable {
    let id: UUID
    let rangeStart: Double
    let rangeEnd: Double
    let count: Int
    let percentage: Double
    
    var label: String {
        String(format: "%.1f-%.1f", rangeStart, rangeEnd)
    }
    
    enum CodingKeys: String, CodingKey {
        case id
        case rangeStart = "range_start"
        case rangeEnd = "range_end"
        case count
        case percentage
    }
    
    init(id: UUID = UUID(), rangeStart: Double, rangeEnd: Double, count: Int, percentage: Double) {
        self.id = id
        self.rangeStart = rangeStart
        self.rangeEnd = rangeEnd
        self.count = count
        self.percentage = percentage
    }
}

// MARK: - Analysis

struct Analysis: Codable, Identifiable, Hashable {
    let id: UUID
    let name: String
    let analysisType: AnalysisType
    let status: AnalysisStatus
    let createdAt: Date
    let updatedAt: Date
    let completedAt: Date?
    let sampleId: String?
    let patientId: String?
    let notes: String?
    let imageCount: Int
    let serverAnalysisId: String?
    let resultId: UUID?
    let localImagePaths: [String]
    let isSynced: Bool
    
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: createdAt)
    }
    
    var elapsedTime: String {
        let interval = Date().timeIntervalSince(createdAt)
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.day, .hour, .minute]
        formatter.unitsStyle = .abbreviated
        formatter.maximumUnitCount = 2
        return formatter.string(from: interval) ?? "Unknown"
    }
    
    static func == (lhs: Analysis, rhs: Analysis) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
    
    enum CodingKeys: String, CodingKey {
        case id, name, status, notes
        case analysisType = "analysis_type"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case completedAt = "completed_at"
        case sampleId = "sample_id"
        case patientId = "patient_id"
        case imageCount = "image_count"
        case serverAnalysisId = "server_analysis_id"
        case resultId = "result_id"
        case localImagePaths = "local_image_paths"
        case isSynced = "is_synced"
    }
    
    init(
        id: UUID = UUID(),
        name: String,
        analysisType: AnalysisType,
        status: AnalysisStatus = .pending,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        completedAt: Date? = nil,
        sampleId: String? = nil,
        patientId: String? = nil,
        notes: String? = nil,
        imageCount: Int = 0,
        serverAnalysisId: String? = nil,
        resultId: UUID? = nil,
        localImagePaths: [String] = [],
        isSynced: Bool = false
    ) {
        self.id = id
        self.name = name
        self.analysisType = analysisType
        self.status = status
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.completedAt = completedAt
        self.sampleId = sampleId
        self.patientId = patientId
        self.notes = notes
        self.imageCount = imageCount
        self.serverAnalysisId = serverAnalysisId
        self.resultId = resultId
        self.localImagePaths = localImagePaths
        self.isSynced = isSynced
    }
}

// MARK: - User Profile

struct UserProfile: Codable {
    let id: UUID
    var username: String
    var email: String
    var fullName: String
    var institution: String?
    var role: String?
    var avatarURL: String?
    var totalAnalyses: Int
    var joinedDate: Date
    
    enum CodingKeys: String, CodingKey {
        case id, username, email, institution, role
        case fullName = "full_name"
        case avatarURL = "avatar_url"
        case totalAnalyses = "total_analyses"
        case joinedDate = "joined_date"
    }
    
    init(
        id: UUID = UUID(),
        username: String = "",
        email: String = "",
        fullName: String = "",
        institution: String? = nil,
        role: String? = nil,
        avatarURL: String? = nil,
        totalAnalyses: Int = 0,
        joinedDate: Date = Date()
    ) {
        self.id = id
        self.username = username
        self.email = email
        self.fullName = fullName
        self.institution = institution
        self.role = role
        self.avatarURL = avatarURL
        self.totalAnalyses = totalAnalyses
        self.joinedDate = joinedDate
    }
}

// MARK: - API Response Models

struct LoginResponse: Codable {
    let token: String
    let refreshToken: String?
    let expiresIn: Int
    let user: UserProfile
    
    enum CodingKeys: String, CodingKey {
        case token, user
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
    }
}

struct UploadResponse: Codable {
    let analysisId: String
    let status: String
    let message: String
    
    enum CodingKeys: String, CodingKey {
        case analysisId = "analysis_id"
        case status, message
    }
}

struct AnalysisListResponse: Codable {
    let analyses: [Analysis]
    let totalCount: Int
    let page: Int
    let pageSize: Int
    
    enum CodingKeys: String, CodingKey {
        case analyses, page
        case totalCount = "total_count"
        case pageSize = "page_size"
    }
}

struct APIError: Codable {
    let code: String
    let message: String
    let details: String?
}

// MARK: - Longitudinal Data Point

struct LongitudinalDataPoint: Codable, Identifiable {
    let id: UUID
    let date: Date
    let meanTelomereLength: Double
    let analysisId: UUID
    
    enum CodingKeys: String, CodingKey {
        case id, date
        case meanTelomereLength = "mean_telomere_length"
        case analysisId = "analysis_id"
    }
    
    init(id: UUID = UUID(), date: Date, meanTelomereLength: Double, analysisId: UUID) {
        self.id = id
        self.date = date
        self.meanTelomereLength = meanTelomereLength
        self.analysisId = analysisId
    }
}

// MARK: - Sample Data Generator

extension Analysis {
    static var sampleData: [Analysis] {
        [
            Analysis(
                name: "Sample TL-2024-001",
                analysisType: .telomereLength,
                status: .completed,
                createdAt: Calendar.current.date(byAdding: .hour, value: -2, to: Date()) ?? Date(),
                sampleId: "BLD-001",
                patientId: "PT-1001",
                imageCount: 15,
                isSynced: true
            ),
            Analysis(
                name: "Q-FISH Batch 042",
                analysisType: .qFISH,
                status: .processing,
                createdAt: Calendar.current.date(byAdding: .minute, value: -45, to: Date()) ?? Date(),
                sampleId: "BLD-002",
                imageCount: 8
            ),
            Analysis(
                name: "Aberration Screen A",
                analysisType: .chromosomeAberration,
                status: .completed,
                createdAt: Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date(),
                sampleId: "TIS-003",
                patientId: "PT-1002",
                imageCount: 22,
                isSynced: true
            ),
            Analysis(
                name: "Flow-FISH Run 12",
                analysisType: .flowFISH,
                status: .pending,
                createdAt: Calendar.current.date(byAdding: .day, value: -3, to: Date()) ?? Date(),
                sampleId: "BLD-004",
                imageCount: 0
            ),
            Analysis(
                name: "Fluorescence Int. B7",
                analysisType: .fluorescenceIntensity,
                status: .failed,
                createdAt: Calendar.current.date(byAdding: .day, value: -5, to: Date()) ?? Date(),
                sampleId: "TIS-005",
                notes: "Image quality too low for reliable analysis",
                imageCount: 3
            ),
        ]
    }
}

extension TelomereResult {
    static var sampleResult: TelomereResult {
        let chromosomes = (1...22).map { num in
            ChromosomeData(
                chromosomeNumber: num,
                pArmLength: Double.random(in: 3.0...12.0),
                qArmLength: Double.random(in: 3.0...12.0),
                averageLength: Double.random(in: 3.5...11.0),
                fluorescenceIntensity: Double.random(in: 500...3000),
                aberrationDetected: num == 7 || num == 17,
                aberrationType: num == 7 ? "Dicentric" : (num == 17 ? "Deletion" : nil),
                confidenceScore: Double.random(in: 0.85...0.99)
            )
        }
        
        let distribution = stride(from: 0.0, to: 16.0, by: 2.0).map { start in
            DistributionBin(
                rangeStart: start,
                rangeEnd: start + 2.0,
                count: Int.random(in: 5...50),
                percentage: Double.random(in: 2.0...20.0)
            )
        }
        
        return TelomereResult(
            meanTelomereLength: 7.2,
            medianTelomereLength: 7.0,
            standardDeviation: 2.1,
            shortestTelomere: 2.8,
            longestTelomere: 14.3,
            percentileTenth: 4.1,
            percentileNinetieth: 10.8,
            totalCellsAnalyzed: 150,
            qualityScore: 0.94,
            chromosomeData: chromosomes,
            ageEstimate: 42.5,
            biologicalAgeOffset: -3.2,
            telomereDistribution: distribution
        )
    }
}
