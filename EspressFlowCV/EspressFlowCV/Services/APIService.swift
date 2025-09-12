import Foundation

class APIService {
    private let baseURL = "http://localhost:5000/api"
    private let session = URLSession.shared
    
    // MARK: - Health Check
    func healthCheck() async throws -> [String: Any] {
        guard let url = URL(string: "\(baseURL)/health") else {
            throw APIError.invalidURL
        }
        let (data, _) = try await session.data(from: url)
        guard let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw APIError.invalidResponse
        }
        return result
    }
    
    // MARK: - Get Shots
    func getShots(limit: Int? = nil) async throws -> [EspressoShot] {
        var urlString = "\(baseURL)/shots"
        if let limit = limit {
            urlString += "?limit=\(limit)"
        }
        
        guard let url = URL(string: urlString) else {
            throw APIError.invalidURL
        }
        let (data, _) = try await session.data(from: url)
        
        let response = try JSONDecoder().decode(ShotsResponse.self, from: data)
        return response.shots
    }
    
    // MARK: - Get Summary
    func getSummary() async throws -> ShotsSummary {
        guard let url = URL(string: "\(baseURL)/stats") else {
            throw APIError.invalidURL
        }
        let (data, _) = try await session.data(from: url)
        
        let response = try JSONDecoder().decode(StatsResponse.self, from: data)
        return response.summary
    }
    
    // MARK: - Delete Shot
    func deleteShot(shotId: Int) async throws {
        guard let url = URL(string: "\(baseURL)/shots/\(shotId)") else {
            throw APIError.invalidURL
        }
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
        guard let url = URL(string: "\(baseURL)/analyze") else {
            throw APIError.invalidURL
        }
        
        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        
        // Add video file
        let videoData = try Data(contentsOf: videoURL)
        guard let boundaryData = "--\(boundary)\r\n".data(using: .utf8),
              let headerData = "Content-Disposition: form-data; name=\"video\"; filename=\"espresso_shot.mp4\"\r\n".data(using: .utf8),
              let typeData = "Content-Type: video/mp4\r\n\r\n".data(using: .utf8),
              let endData = "\r\n".data(using: .utf8) else {
            throw APIError.encodingError
        }
        body.append(boundaryData)
        body.append(headerData)
        body.append(typeData)
        body.append(videoData)
        body.append(endData)
        
        // Add metadata if provided
        if !metadata.isEmpty {
            let metadataJSON = try JSONSerialization.data(withJSONObject: metadata)
            guard let metaBoundaryData = "--\(boundary)\r\n".data(using: .utf8),
                  let metaHeaderData = "Content-Disposition: form-data; name=\"metadata\"\r\n\r\n".data(using: .utf8),
                  let metaEndData = "\r\n".data(using: .utf8) else {
                throw APIError.encodingError
            }
            body.append(metaBoundaryData)
            body.append(metaHeaderData)
            body.append(metadataJSON)
            body.append(metaEndData)
        }
        
        guard let finalBoundaryData = "--\(boundary)--\r\n".data(using: .utf8) else {
            throw APIError.encodingError
        }
        body.append(finalBoundaryData)
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
    case invalidURL
    case encodingError
    
    var errorDescription: String? {
        switch self {
        case .deleteFailed:
            return "Failed to delete shot"
        case .analysisRequestFailed:
            return "Video analysis request failed"
        case .invalidResponse:
            return "Invalid response from server"
        case .invalidURL:
            return "Invalid API URL"
        case .encodingError:
            return "Data encoding error"
        }
    }
}