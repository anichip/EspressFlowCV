import Foundation

class APIService {
    private let baseURL = "http://localhost:5000/api"
    private let session = URLSession.shared
    
    // MARK: - Health Check
    func healthCheck() async throws -> [String: Any] {
        let url = URL(string: "\(baseURL)/health")!
        let (data, _) = try await session.data(from: url)
        return try JSONSerialization.jsonObject(with: data) as! [String: Any]
    }
    
    // MARK: - Get Shots
    func getShots(limit: Int? = nil) async throws -> [EspressoShot] {
        var urlString = "\(baseURL)/shots"
        if let limit = limit {
            urlString += "?limit=\(limit)"
        }
        
        let url = URL(string: urlString)!
        let (data, _) = try await session.data(from: url)
        
        let response = try JSONDecoder().decode(ShotsResponse.self, from: data)
        return response.shots
    }
    
    // MARK: - Get Summary
    func getSummary() async throws -> ShotsSummary {
        let url = URL(string: "\(baseURL)/stats")!
        let (data, _) = try await session.data(from: url)
        
        let response = try JSONDecoder().decode(StatsResponse.self, from: data)
        return response.summary
    }
    
    // MARK: - Delete Shot
    func deleteShot(shotId: Int) async throws {
        let url = URL(string: "\(baseURL)/shots/\(shotId)")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        
        let (_, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.deleteFailed
        }
    }
    
    // MARK: - Analyze Video
    func analyzeVideo(videoURL: URL, metadata: [String: Any] = [:]) async throws -> EspressoShot {
        let url = URL(string: "\(baseURL)/analyze")!
        
        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        
        // Add video file
        let videoData = try Data(contentsOf: videoURL)
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"video\"; filename=\"espresso_shot.mp4\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: video/mp4\r\n\r\n".data(using: .utf8)!)
        body.append(videoData)
        body.append("\r\n".data(using: .utf8)!)
        
        // Add metadata if provided
        if !metadata.isEmpty {
            let metadataJSON = try JSONSerialization.data(withJSONObject: metadata)
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"metadata\"\r\n\r\n".data(using: .utf8)!)
            body.append(metadataJSON)
            body.append("\r\n".data(using: .utf8)!)
        }
        
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.analysisRequestFailed
        }
        
        let analysisResponse = try JSONDecoder().decode(AnalysisResponse.self, from: data)
        
        // Convert to EspressoShot
        return EspressoShot(
            id: analysisResponse.shotId,
            filename: analysisResponse.filename,
            recordedAt: Date(),
            analysisResult: analysisResponse.analysisResult,
            confidence: analysisResponse.confidence,
            features: analysisResponse.features,
            videoDurationS: nil,
            notes: ""
        )
    }
}

// MARK: - Response Models
private struct ShotsResponse: Codable {
    let shots: [EspressoShot]
    let count: Int
}

private struct StatsResponse: Codable {
    let summary: ShotsSummary
}

private struct AnalysisResponse: Codable {
    let shotId: Int
    let filename: String
    let analysisResult: String
    let confidence: Double
    let features: [String: Double]
    
    enum CodingKeys: String, CodingKey {
        case shotId = "shot_id"
        case filename
        case analysisResult = "analysis_result"
        case confidence
        case features
    }
}

// MARK: - Errors
enum APIError: Error, LocalizedError {
    case deleteFailed
    case analysisRequestFailed
    case invalidResponse
    
    var errorDescription: String? {
        switch self {
        case .deleteFailed:
            return "Failed to delete shot"
        case .analysisRequestFailed:
            return "Video analysis request failed"
        case .invalidResponse:
            return "Invalid response from server"
        }
    }
}