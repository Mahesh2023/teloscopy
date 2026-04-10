// SyncManager.swift
// Teloscopy
//
// Manages offline data persistence and background synchronization.
// Queues uploads and syncs results when network connectivity is restored.
//

import Foundation
import Combine
import Network
import UIKit

// MARK: - Sync State

enum SyncState: Equatable {
    case idle
    case syncing
    case uploading(progress: Double)
    case error(String)
    case completed
    
    var displayName: String {
        switch self {
        case .idle: return "Up to date"
        case .syncing: return "Syncing..."
        case .uploading(let progress): return "Uploading \(Int(progress * 100))%"
        case .error(let message): return "Error: \(message)"
        case .completed: return "Sync complete"
        }
    }
    
    static func == (lhs: SyncState, rhs: SyncState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle), (.syncing, .syncing), (.completed, .completed):
            return true
        case (.uploading(let a), .uploading(let b)):
            return a == b
        case (.error(let a), .error(let b)):
            return a == b
        default:
            return false
        }
    }
}

// MARK: - Pending Upload

struct PendingUpload: Codable, Identifiable {
    let id: UUID
    let analysisId: UUID
    let localImagePath: String
    let fileName: String
    let createdAt: Date
    var retryCount: Int
    var lastError: String?
    
    static let maxRetries = 3
    var canRetry: Bool { retryCount < Self.maxRetries }
}

// MARK: - Sync Manager

final class SyncManager: ObservableObject {
    static let shared = SyncManager()
    
    @Published var syncState: SyncState = .idle
    @Published var pendingUploads: [PendingUpload] = []
    @Published var isNetworkAvailable = true
    @Published var lastSyncDate: Date?
    @Published var cachedAnalyses: [Analysis] = []
    
    private let apiService = APIService.shared
    private let networkMonitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "com.teloscopy.ios.networkmonitor")
    private let syncQueue = DispatchQueue(label: "com.teloscopy.ios.sync", qos: .utility)
    private var cancellables = Set<AnyCancellable>()
    private var syncTimer: Timer?
    
    private let fileManager = FileManager.default
    private var documentsDirectory: URL {
        fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    
    private var cacheDirectory: URL {
        let dir = documentsDirectory.appendingPathComponent("teloscopy_cache", isDirectory: true)
        try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }
    
    private var uploadsDirectory: URL {
        let dir = documentsDirectory.appendingPathComponent("pending_uploads", isDirectory: true)
        try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }
    
    private init() {
        setupNetworkMonitoring()
        loadCachedData()
        startPeriodicSync()
    }
    
    deinit {
        networkMonitor.cancel()
        syncTimer?.invalidate()
    }
    
    // MARK: - Network Monitoring
    
    private func setupNetworkMonitoring() {
        networkMonitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                let wasOffline = !(self?.isNetworkAvailable ?? true)
                self?.isNetworkAvailable = path.status == .satisfied
                
                if wasOffline && path.status == .satisfied {
                    self?.performSync()
                }
            }
        }
        networkMonitor.start(queue: monitorQueue)
    }
    
    // MARK: - Periodic Sync
    
    private func startPeriodicSync() {
        syncTimer = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { [weak self] _ in
            self?.performSync()
        }
    }
    
    // MARK: - Data Persistence
    
    func saveAnalysisLocally(_ analysis: Analysis) {
        var analyses = cachedAnalyses
        if let index = analyses.firstIndex(where: { $0.id == analysis.id }) {
            analyses[index] = analysis
        } else {
            analyses.insert(analysis, at: 0)
        }
        cachedAnalyses = analyses
        persistAnalyses(analyses)
    }
    
    func saveAnalysesLocally(_ analyses: [Analysis]) {
        cachedAnalyses = analyses
        persistAnalyses(analyses)
    }
    
    func deleteLocalAnalysis(_ analysis: Analysis) {
        cachedAnalyses.removeAll { $0.id == analysis.id }
        persistAnalyses(cachedAnalyses)
        for path in analysis.localImagePaths {
            try? fileManager.removeItem(atPath: path)
        }
    }
    
    func saveResultLocally(_ result: TelomereResult, for analysisId: UUID) {
        let resultURL = cacheDirectory.appendingPathComponent("result_\(analysisId.uuidString).json")
        if let data = try? JSONEncoder().encode(result) {
            try? data.write(to: resultURL)
        }
    }
    
    func loadCachedResult(for analysisId: UUID) -> TelomereResult? {
        let resultURL = cacheDirectory.appendingPathComponent("result_\(analysisId.uuidString).json")
        guard let data = try? Data(contentsOf: resultURL) else { return nil }
        return try? JSONDecoder().decode(TelomereResult.self, from: data)
    }
    
    // MARK: - Image Storage
    
    func saveImageLocally(_ imageData: Data, fileName: String) -> String? {
        let imageURL = uploadsDirectory.appendingPathComponent(fileName)
        do {
            try imageData.write(to: imageURL)
            return imageURL.path
        } catch {
            print("[SyncManager] Failed to save image: \(error)")
            return nil
        }
    }
    
    func loadLocalImage(at path: String) -> Data? {
        return fileManager.contents(atPath: path)
    }
    
    // MARK: - Upload Queue
    
    func queueUpload(analysisId: UUID, localImagePath: String, fileName: String) {
        let upload = PendingUpload(
            id: UUID(),
            analysisId: analysisId,
            localImagePath: localImagePath,
            fileName: fileName,
            createdAt: Date(),
            retryCount: 0
        )
        pendingUploads.append(upload)
        persistPendingUploads()
        
        if isNetworkAvailable {
            processUploadQueue()
        }
    }
    
    func removeFromQueue(_ uploadId: UUID) {
        pendingUploads.removeAll { $0.id == uploadId }
        persistPendingUploads()
    }
    
    func clearUploadQueue() {
        for upload in pendingUploads {
            try? fileManager.removeItem(atPath: upload.localImagePath)
        }
        pendingUploads.removeAll()
        persistPendingUploads()
    }
    
    // MARK: - Sync Operations
    
    func performSync() {
        guard isNetworkAvailable else {
            syncState = .error("No network connection")
            return
        }
        guard syncState != .syncing else { return }
        
        syncState = .syncing
        processUploadQueue()
        
        apiService.fetchAnalyses()
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    switch completion {
                    case .finished:
                        self?.syncState = .completed
                        self?.lastSyncDate = Date()
                        UserDefaults.standard.set(Date(), forKey: "last_sync_date")
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            if self?.syncState == .completed {
                                self?.syncState = .idle
                            }
                        }
                    case .failure(let error):
                        self?.syncState = .error(error.localizedDescription)
                    }
                },
                receiveValue: { [weak self] serverAnalyses in
                    self?.mergeServerData(serverAnalyses)
                }
            )
            .store(in: &cancellables)
    }
    
    // MARK: - Private Helpers
    
    private func processUploadQueue() {
        let uploadsToProcess = pendingUploads.filter { $0.canRetry }
        
        for (index, upload) in uploadsToProcess.enumerated() {
            guard let imageData = loadLocalImage(at: upload.localImagePath) else {
                removeFromQueue(upload.id)
                continue
            }
            
            let progress = Double(index) / Double(max(uploadsToProcess.count, 1))
            syncState = .uploading(progress: progress)
            
            apiService.uploadImage(
                analysisId: upload.analysisId.uuidString,
                imageData: imageData,
                fileName: upload.fileName
            )
            .receive(on: DispatchQueue.main)
            .sink(
                receiveCompletion: { [weak self] completion in
                    switch completion {
                    case .finished:
                        self?.removeFromQueue(upload.id)
                        try? FileManager.default.removeItem(atPath: upload.localImagePath)
                    case .failure(let error):
                        if let idx = self?.pendingUploads.firstIndex(where: { $0.id == upload.id }) {
                            self?.pendingUploads[idx].retryCount += 1
                            self?.pendingUploads[idx].lastError = error.localizedDescription
                            self?.persistPendingUploads()
                        }
                    }
                },
                receiveValue: { _ in }
            )
            .store(in: &cancellables)
        }
    }
    
    private func mergeServerData(_ serverAnalyses: [Analysis]) {
        var merged = cachedAnalyses
        for serverAnalysis in serverAnalyses {
            if let localIndex = merged.firstIndex(where: { $0.id == serverAnalysis.id }) {
                merged[localIndex] = serverAnalysis
            } else {
                merged.append(serverAnalysis)
            }
        }
        merged.sort { $0.createdAt > $1.createdAt }
        cachedAnalyses = merged
        persistAnalyses(merged)
    }
    
    private func loadCachedData() {
        let analysesURL = cacheDirectory.appendingPathComponent("analyses.json")
        if let data = try? Data(contentsOf: analysesURL),
           let analyses = try? JSONDecoder().decode([Analysis].self, from: data) {
            cachedAnalyses = analyses
        }
        
        let uploadsURL = cacheDirectory.appendingPathComponent("pending_uploads.json")
        if let data = try? Data(contentsOf: uploadsURL),
           let uploads = try? JSONDecoder().decode([PendingUpload].self, from: data) {
            pendingUploads = uploads
        }
        
        lastSyncDate = UserDefaults.standard.object(forKey: "last_sync_date") as? Date
    }
    
    private func persistAnalyses(_ analyses: [Analysis]) {
        let url = cacheDirectory.appendingPathComponent("analyses.json")
        if let data = try? JSONEncoder().encode(analyses) {
            try? data.write(to: url)
        }
    }
    
    private func persistPendingUploads() {
        let url = cacheDirectory.appendingPathComponent("pending_uploads.json")
        if let data = try? JSONEncoder().encode(pendingUploads) {
            try? data.write(to: url)
        }
    }
    
    // MARK: - Storage Info
    
    var cacheSize: String {
        let size = directorySize(url: cacheDirectory) + directorySize(url: uploadsDirectory)
        return ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file)
    }
    
    func clearCache() {
        try? fileManager.removeItem(at: cacheDirectory)
        try? fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
        cachedAnalyses.removeAll()
    }
    
    private func directorySize(url: URL) -> UInt64 {
        guard let enumerator = fileManager.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey]) else {
            return 0
        }
        var totalSize: UInt64 = 0
        for case let fileURL as URL in enumerator {
            if let size = try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize {
                totalSize += UInt64(size)
            }
        }
        return totalSize
    }
}
