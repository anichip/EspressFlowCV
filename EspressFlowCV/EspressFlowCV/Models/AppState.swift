import Foundation
import Combine

// MARK: - Data Models
struct EspressoShot: Identifiable, Codable {
    let id: Int
    let filename: String
    let recordedAt: Date
    let analysisResult: String // "good" or "under"
    let confidence: Double
    let features: [String: Double]?
    let videoDurationS: Double?
    let notes: String

    enum CodingKeys: String, CodingKey {
        case id
        case filename
        case recordedAt = "recorded_at"
        case analysisResult = "analysis_result"
        case confidence
        case features
        case videoDurationS = "video_duration_s"
        case notes
        // Ignore extra fields from API: created_at, updated_at, features_json
    }

    // Regular memberwise initializer
    init(id: Int, filename: String, recordedAt: Date, analysisResult: String, confidence: Double, features: [String: Double]?, videoDurationS: Double?, notes: String) {
        self.id = id
        self.filename = filename
        self.recordedAt = recordedAt
        self.analysisResult = analysisResult
        self.confidence = confidence
        self.features = features
        self.videoDurationS = videoDurationS
        self.notes = notes
    }

    // Custom decoder to handle extra fields and date parsing
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        id = try container.decode(Int.self, forKey: .id)
        filename = try container.decode(String.self, forKey: .filename)
        analysisResult = try container.decode(String.self, forKey: .analysisResult)
        confidence = try container.decode(Double.self, forKey: .confidence)
        // Handle features - skip entirely for now since it contains mixed types
        features = nil
        print("⚠️ Skipping features parsing due to mixed types (string + double)")
        videoDurationS = try container.decodeIfPresent(Double.self, forKey: .videoDurationS)
        notes = try container.decode(String.self, forKey: .notes)

        // Handle date parsing - API returns ISO string
        let dateString = try container.decode(String.self, forKey: .recordedAt)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        recordedAt = formatter.date(from: dateString) ?? Date()
    }

    // Custom encoder to maintain compatibility
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        try container.encode(id, forKey: .id)
        try container.encode(filename, forKey: .filename)
        try container.encode(analysisResult, forKey: .analysisResult)
        try container.encode(confidence, forKey: .confidence)
        try container.encodeIfPresent(features, forKey: .features)
        try container.encodeIfPresent(videoDurationS, forKey: .videoDurationS)
        try container.encode(notes, forKey: .notes)

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        try container.encode(formatter.string(from: recordedAt), forKey: .recordedAt)
    }
    
    var isGoodShot: Bool {
        return analysisResult == "good"
    }
    
    var displayResult: String {
        return isGoodShot ? "Great Pull!" : "Slightly Under"
    }
    
    var resultColor: String {
        return isGoodShot ? "green" : "orange"
    }
}

struct ShotsSummary: Codable {
    let totalShots: Int
    let goodShots: Int
    let underShots: Int
    let goodPercentage: Double
    let underPercentage: Double
    
    enum CodingKeys: String, CodingKey {
        case totalShots = "total_shots"
        case goodShots = "good_shots"
        case underShots = "under_shots"
        case goodPercentage = "good_percentage"
        case underPercentage = "under_percentage"
    }
}

// MARK: - App State Management
class AppState: ObservableObject {
    @Published var shots: [EspressoShot] = []
    @Published var summary: ShotsSummary?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let apiService = APIService()
    
    init() {
        loadData()
    }
    
    func loadData() {
        Task {
            await refreshShots()
            await refreshSummary()
        }
    }
    
    @MainActor
    func refreshShots() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let shots = try await apiService.getShots()
            self.shots = shots
        } catch {
            self.errorMessage = "Failed to load shots: \(error.localizedDescription)"
        }
        
        isLoading = false
    }
    
    @MainActor
    func refreshSummary() async {
        do {
            let summary = try await apiService.getSummary()
            self.summary = summary
        } catch {
            print("Failed to load summary: \(error)")
        }
    }
    
    @MainActor
    func addNewShot(_ shot: EspressoShot) {
        shots.insert(shot, at: 0) // Add to beginning
        // Refresh summary to update counts
        Task {
            await refreshSummary()
        }
    }
    
    @MainActor
    func deleteShot(_ shot: EspressoShot) async {
        do {
            try await apiService.deleteShot(shotId: shot.id)
            shots.removeAll { $0.id == shot.id }
            await refreshSummary()
        } catch {
            errorMessage = "Failed to delete shot: \(error.localizedDescription)"
        }
    }
}