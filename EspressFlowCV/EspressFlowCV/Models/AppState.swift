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
    @Published var isRetrying = false

    private let apiService = APIService()
    private var retryCount = 0
    private let maxRetries = 3

    init() {
        loadData()
    }
    
    func loadData() {
        // Load shots from local storage first
        loadShotsFromLocalStorage()

        Task {
            await performInitialSetup()
        }
    }

    private func loadShotsFromLocalStorage() {
        if let data = UserDefaults.standard.data(forKey: "savedShots"),
           let decodedShots = try? JSONDecoder().decode([EspressoShot].self, from: data) {
            self.shots = decodedShots
            print("📱 Loaded \(decodedShots.count) shots from local storage")
        } else {
            print("📱 No shots found in local storage")
        }
    }

    private func saveShotsToLocalStorage() {
        if let encoded = try? JSONEncoder().encode(shots) {
            UserDefaults.standard.set(encoded, forKey: "savedShots")
            print("💾 Saved \(shots.count) shots to local storage")
        }
    }

    @MainActor
    private func performInitialSetup() async {
        // First, try to discover a working server
        print("🔍 Performing initial server discovery...")
        let serverFound = await apiService.discoverServer()

        if serverFound {
            print("✅ Server discovered, loading data...")
            // Skip server shots refresh - we're using local storage now
            await refreshSummary()
        } else {
            print("❌ No server found during initial setup")
            errorMessage = "Unable to connect to server. Please check your network connection and ensure the API server is running."
        }
    }
    
    @MainActor
    func refreshShots() async {
        isLoading = true
        errorMessage = nil
        retryCount = 0

        await attemptShotsRefresh()
    }

    @MainActor
    private func attemptShotsRefresh() async {
        do {
            let shots = try await apiService.getShots()
            print("📊 Loaded \(shots.count) shots from API")
            self.shots = shots
            self.errorMessage = nil
            self.retryCount = 0
            self.isRetrying = false
        } catch {
            print("❌ Failed to load shots (attempt \(retryCount + 1)): \(error)")

            if retryCount < maxRetries {
                retryCount += 1
                isRetrying = true
                errorMessage = "Retrying connection... (attempt \(retryCount)/\(maxRetries))"

                // Exponential backoff: 1s, 2s, 4s
                let delay = TimeInterval(pow(2.0, Double(retryCount - 1)))
                print("🔄 Retrying in \(delay) seconds...")

                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                await attemptShotsRefresh()
            } else {
                isRetrying = false
                errorMessage = error.localizedDescription
            }
        }

        isLoading = false
    }

    @MainActor
    func retryConnection() async {
        guard !isLoading && !isRetrying else { return }
        retryCount = 0
        await refreshShots()
    }
    
    @MainActor
    func refreshSummary() async {
        // Calculate summary from local shots data instead of server
        let totalShots = shots.count
        let goodShots = shots.filter { $0.isGoodShot }.count
        let underShots = totalShots - goodShots

        let goodPercentage = totalShots > 0 ? (Double(goodShots) / Double(totalShots)) * 100 : 0
        let underPercentage = totalShots > 0 ? (Double(underShots) / Double(totalShots)) * 100 : 0

        self.summary = ShotsSummary(
            totalShots: totalShots,
            goodShots: goodShots,
            underShots: underShots,
            goodPercentage: goodPercentage,
            underPercentage: underPercentage
        )
    }
    
    @MainActor
    func addNewShot(_ shot: EspressoShot) {
        shots.insert(shot, at: 0) // Add to beginning
        saveShotsToLocalStorage() // Save to device storage
        // Refresh summary to update counts
        Task {
            await refreshSummary()
        }
    }
    
    @MainActor
    func deleteShot(_ shot: EspressoShot) async {
        // Remove from local storage only (no server call needed)
        shots.removeAll { $0.id == shot.id }
        saveShotsToLocalStorage() // Save updated list to device
        await refreshSummary()
    }
}