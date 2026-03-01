import AVFoundation
import Accelerate

class AudioEngineManager: ObservableObject {
    private let audioEngine = AVAudioEngine()
    private let mixer = AVAudioMixerNode()
    
    @Published var livePitch: Float = 0.0
    
    // FFT parameters
    private let fftSize = 1024
    private lazy var fftSetup = vDSP_create_fftsetup(vDSP_Length(log2(Float(fftSize))), FFTRadix(kFFTRadix2))
    
    init() {
        setupEngine()
    }
    
    private func setupEngine() {
        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.inputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: AVAudioFrameCount(fftSize), format: inputFormat) { [weak self] (buffer, time) in
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
        guard let channelData = buffer.floatChannelData?[0] else { return }
        let frameCount = Int(buffer.frameLength)
        
        // 1. Windowing (Hann window)
        var window = [Float](repeating: 0, count: fftSize)
        vDSP_hann_window(&window, vDSP_Length(fftSize), Int32(vDSP_HANN_NORM))
        var windowedData = [Float](repeating: 0, count: fftSize)
        vDSP_vmul(channelData, 1, window, 1, &windowedData, 1, vDSP_Length(fftSize))
        
        // 2. FFT
        var real = [Float](repeating: 0, count: fftSize / 2)
        var imag = [Float](repeating: 0, count: fftSize / 2)
        var splitComplex = DSPSplitComplex(realp: &real, imagp: &imag)
        
        windowedData.withUnsafeBytes { (ptr: UnsafeRawBufferPointer) in
            let floatPtr = ptr.bindMemory(to: Float.self).baseAddress!
            vDSP_ctoz(UnsafePointer<DSPComplex>(OpaquePointer(floatPtr)), 2, &splitComplex, 1, vDSP_Length(fftSize / 2))
        }
        
        vDSP_fft_zrip(fftSetup!, &splitComplex, 1, vDSP_Length(log2(Float(fftSize))), Int32(FFT_FORWARD))
        
        // 3. Magnitude calculation
        var magnitudes = [Float](repeating: 0, count: fftSize / 2)
        vDSP_zvmags(&splitComplex, 1, &magnitudes, 1, vDSP_Length(fftSize / 2))
        
        // 4. Find peak frequency
        var maxMag: Float = 0
        var maxIdx: vDSP_Length = 0
        vDSP_maxvi(&magnitudes, 1, &maxMag, &maxIdx, vDSP_Length(fftSize / 2))
        
        let sampleRate = Float(buffer.format.sampleRate)
        let frequency = Float(maxIdx) * (sampleRate / Float(fftSize))
        
        DispatchQueue.main.async {
            self.livePitch = frequency
        }
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
    
    deinit {
        if let setup = fftSetup {
            vDSP_destroy_fftsetup(setup)
        }
    }
}
