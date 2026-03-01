import Foundation

struct PitchData: Codable {
    let pitch: [Float]
    let sr: Int
}

class PitchManager: ObservableObject {
    @Published var targetPitch: Float = 0.0
    private var pitchTimeline: [Float] = []
    private var sampleRate: Int = 22050 // Default from backend
    
    func loadPitchData(from url: URL) {
        do {
            let data = try Data(contentsOf: url)
            let decoded = try JSONDecoder().decode(PitchData.self, from: data)
            self.pitchTimeline = decoded.pitch
            self.sampleRate = decoded.sr
        } catch {
            print("Error loading pitch data: \(error)")
        }
    }
    
    func updateTargetPitch(forTime time: TimeInterval) {
        // The backend pitch extraction uses a specific hop length.
        // Librosa's pyin default hop_length is 512.
        let hopLength = 512
        let index = Int((time * Double(sampleRate)) / Double(hopLength))
        
        if index >= 0 && index < pitchTimeline.count {
            DispatchQueue.main.async {
                self.targetPitch = self.pitchTimeline[index]
            }
        }
    }
}
