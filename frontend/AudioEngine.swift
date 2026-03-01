import AVFoundation
import Accelerate

class AudioEngineManager: ObservableObject {
    private let audioEngine = AVAudioEngine()
    private let mixer = AVAudioMixerNode()
    
    @Published var livePitch: Float = 0.0
    
    init() {
        setupEngine()
    }
    
    private func setupEngine() {
        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.inputFormat(forBus: 0)
        
        // Setup mic capture for real-time FFT
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] (buffer, time) in
            self?.analyzePitch(buffer: buffer)
        }
        
        audioEngine.attach(mixer)
        audioEngine.connect(mixer, to: audioEngine.mainMixerNode, format: nil)
    }
    
    func start() throws {
        try audioEngine.start()
    }
    
    func stop() {
        audioEngine.stop()
    }
    
    private func analyzePitch(buffer: AVAudioPCMBuffer) {
        // Placeholder for FFT logic using Accelerate framework
        // This would calculate the dominant frequency and update livePitch
    }
    
    func playInstrumental(url: URL) {
        let player = AVAudioPlayerNode()
        audioEngine.attach(player)
        audioEngine.connect(player, to: mixer, format: nil)
        
        if let file = try? AVAudioFile(forReading: url) {
            player.scheduleFile(file, at: nil)
            player.play()
        }
    }
}
