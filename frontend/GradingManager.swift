import Foundation

class GradingManager: ObservableObject {
    @Published var currentScore: Double = 0.0
    @Published var lastAccuracy: Double = 0.0
    
    // Constants for grading
    private let perfectTolerance: Float = 5.0 // Hz
    private let goodTolerance: Float = 15.0 // Hz
    
    func gradePitch(live: Float, target: Float) {
        guard target > 0 && live > 0 else {
            lastAccuracy = 0
            return
        }
        
        let diff = abs(live - target)
        var accuracy: Double = 0.0
        
        if diff <= perfectTolerance {
            accuracy = 1.0
        } else if diff <= goodTolerance {
            accuracy = 0.5
        } else {
            accuracy = 0.0
        }
        
        DispatchQueue.main.async {
            self.lastAccuracy = accuracy
            self.currentScore += accuracy
        }
    }
    
    func reset() {
        currentScore = 0.0
        lastAccuracy = 0.0
    }
}
