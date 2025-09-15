import Foundation

class APIService {
    private var baseURL: String = ""
    private let session: URLSession

    // Candidate URLs to try in order of preference
    private let candidateURLs = [
        "http://localhost:5000",        // Local development
        "http://127.0.0.1:5000",       // Local fallback
        "http://192.168.86.53:5000",   // Your home WiFi
        "http://192.168.1.53:5000",    // Common router range
        "http://10.0.0.53:5000"        // Another common range
    ]

    init() {
        // Configure session with timeout
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10.0
        config.timeoutIntervalForResource = 30.0
        self.session = URLSession(configuration: config)

        // Initialize with localhost as default
        self.baseURL = candidateURLs[0]
    }

    // MARK: - Server Discovery
    func discoverServer() async -> Bool {
        print("🔍 Discovering available server...")

        for candidateURL in candidateURLs {
            print("🌐 Trying: \(candidateURL)")

            do {
                guard let url = URL(string: "\(candidateURL)/api/health") else { continue }
                let (data, response) = try await session.data(from: url)

                guard let httpResponse = response as? HTTPURLResponse,
                      httpResponse.statusCode == 200 else { continue }

                if let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   result["status"] as? String == "healthy" {
                    print("✅ Found working server at: \(candidateURL)")
                    self.baseURL = candidateURL
                    return true
                }
            } catch {
                print("❌ Failed to connect to \(candidateURL): \(error.localizedDescription)")
                continue
            }
        }

        print("🚨 No working server found in candidate list")
        return false
    }

    // MARK: - Request Helper with Auto-Discovery
    private func performRequestWithDiscovery<T>(request: () async throws -> T) async throws -> T {
        do {
            // First attempt with current baseURL
            return try await request()
        } catch {
            print("🔄 Request failed, attempting server discovery...")

            // If request fails, try to discover a working server
            let discovered = await discoverServer()

            if discovered {
                // Retry the request with the new server
                return try await request()
            } else {
                // If no server found, throw the original error
                throw APIError.serverNotAvailable
            }
        }
    }

    // MARK: - Health Check
    func healthCheck() async throws -> [String: Any] {
        return try await performRequestWithDiscovery {
            guard let url = URL(string: "\(self.baseURL)/api/health") else {
                throw APIError.invalidURL
            }
            let (data, _) = try await self.session.data(from: url)
            guard let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw APIError.invalidResponse
            }
            return result
        }
    }

    // Quick connectivity check without discovery (for proactive health checks)
    func quickHealthCheck() async -> Bool {
        do {
            guard let url = URL(string: "\(baseURL)/api/health") else { return false }
            let (data, response) = try await session.data(from: url)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200,
                  let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  result["status"] as? String == "healthy" else {
                return false
            }

            return true
        } catch {
            return false
        }
    }
    
    // MARK: - Get Shots
    func getShots(limit: Int? = nil) async throws -> [EspressoShot] {
        return try await performRequestWithDiscovery {
            var urlString = "\(self.baseURL)/api/shots"
            if let limit = limit {
                urlString += "?limit=\(limit)"
            }

            guard let url = URL(string: urlString) else {
                throw APIError.invalidURL
            }
            let (data, _) = try await self.session.data(from: url)

            let response = try JSONDecoder().decode(ShotsResponse.self, from: data)
            return response.shots
        }
    }
    
    // MARK: - Get Summary
    func getSummary() async throws -> ShotsSummary {
        return try await performRequestWithDiscovery {
            guard let url = URL(string: "\(self.baseURL)/api/stats") else {
                throw APIError.invalidURL
            }
            let (data, _) = try await self.session.data(from: url)

            let response = try JSONDecoder().decode(StatsResponse.self, from: data)
            return response.summary
        }
    }
    
    // MARK: - Delete Shot
    func deleteShot(shotId: Int) async throws {
        try await performRequestWithDiscovery {
            guard let url = URL(string: "\(self.baseURL)/api/shots/\(shotId)") else {
                throw APIError.invalidURL
            }
            var request = URLRequest(url: url)
            request.httpMethod = "DELETE"

            let (_, response) = try await self.session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw APIError.deleteFailed
            }
        }
    }
    
    // MARK: - Analyze Video
    func analyzeVideo(videoURL: URL, metadata: [String: Any] = [:]) async throws -> EspressoShot {
        return try await performRequestWithDiscovery {
            guard let url = URL(string: "\(self.baseURL)/api/analyze") else {
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

            let (data, response) = try await self.session.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.analysisRequestFailed
            }

            if httpResponse.statusCode != 200 {
                // Try to get error message from server
                let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown server error"
                print("🚨 Server error (\(httpResponse.statusCode)): \(errorMessage)")
                throw APIError.serverError(httpResponse.statusCode, errorMessage)
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
    let features: [String: Double]?

    enum CodingKeys: String, CodingKey {
        case shotId = "shot_id"
        case filename
        case analysisResult = "analysis_result"
        case confidence
        case features
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        shotId = try container.decode(Int.self, forKey: .shotId)
        filename = try container.decode(String.self, forKey: .filename)
        analysisResult = try container.decode(String.self, forKey: .analysisResult)
        confidence = try container.decode(Double.self, forKey: .confidence)

        // Skip features parsing due to mixed types
        features = nil
        print("⚠️ Skipping features parsing in AnalysisResponse due to mixed types")
    }
}

// MARK: - Errors
enum APIError: Error, LocalizedError {
    case deleteFailed
    case analysisRequestFailed
    case invalidResponse
    case invalidURL
    case encodingError
    case serverError(Int, String)
    case serverNotAvailable

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
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        case .serverNotAvailable:
            return "Unable to connect to server. Please check your network connection and ensure the API server is running."
        }
    }
}