import Foundation

class BackendClient: ObservableObject {
    static let shared = BackendClient()
    private let baseURL = "http://127.0.0.1:8000"
    
    struct ProcessingResponse: Codable {
        let status: String
        let message: String
        let output_files: [String]
    }
    
    func uploadAndSeparate(fileURL: URL, mode: String = "vocals") async throws -> ProcessingResponse {
        guard let url = URL(string: "\(baseURL)/separate?mode=\(mode)") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        let fileData = try Data(contentsOf: fileURL)
        var body = Data()
        
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileURL.lastPathComponent)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        let (data, response) = try await URLSession.shared.upload(for: request, from: body)
        
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(ProcessingResponse.self, from: data)
    }
    
    func transcribeVocals(vocalsPath: String) async throws -> ProcessingResponse {
        guard let encodedPath = vocalsPath.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "\(baseURL)/transcribe?vocals_path=\(encodedPath)") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(ProcessingResponse.self, from: data)
    }
    
    func extractPitch(audioPath: String, instrument: String = "vocals") async throws -> ProcessingResponse {
        guard let encodedPath = audioPath.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "\(baseURL)/extract-pitch?audio_path=\(encodedPath)&instrument=\(instrument)") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(ProcessingResponse.self, from: data)
    }
}
