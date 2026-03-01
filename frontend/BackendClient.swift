import Foundation

class BackendClient: ObservableObject {
    static let shared = BackendClient()
    private let baseURL = "http://127.0.0.1:8000"
    
    struct ProcessingResponse: Codable {
        let status: String
        let message: String
        let output_files: [String]
    }
    
    func uploadAndSeparate(fileURL: URL) async throws -> ProcessingResponse {
        guard let url = URL(string: "\(baseURL)/separate") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        let fileData = try Data(contentsOf: fileURL)
        var body = Data()
        
        body.append("--\(boundary)
".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name="file"; filename="\(fileURL.lastPathComponent)"
".data(using: .utf8)!)
        body.append("Content-Type: audio/wav

".data(using: .utf8)!)
        body.append(fileData)
        body.append("
--\(boundary)--
".data(using: .utf8)!)
        
        let (data, response) = try await URLSession.shared.upload(for: request, from: body)
        
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(ProcessingResponse.self, from: data)
    }
    
    func transcribeVocals(filename: String) async throws -> ProcessingResponse {
        guard let url = URL(string: "\(baseURL)/transcribe?filename=\(filename)") else {
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
    
    func extractPitch(filename: String) async throws -> ProcessingResponse {
        guard let url = URL(string: "\(baseURL)/extract-pitch?filename=\(filename)") else {
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
