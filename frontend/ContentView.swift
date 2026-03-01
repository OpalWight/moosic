import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var audioEngine = AudioEngineManager()
    @StateObject private var pitchManager = PitchManager()
    @StateObject private var gradingManager = GradingManager()
    
    @State private var isProcessing = false
    @State private var statusMessage = "Welcome to Moosic"
    @State private var showingFilePicker = false
    @State private var currentTime: TimeInterval = 0.0
    
    @State private var targetHistory: [PitchPoint] = []
    @State private var liveHistory: [PitchPoint] = []
    @State private var selectedInstrument = "vocals"
    
    private let instruments = ["vocals", "piano", "guitar"]
    private let updateInterval = 0.05
    
    var body: some View {
        VStack(spacing: 24) {
            StatusArea(message: statusMessage, isProcessing: isProcessing)
            
            if !isProcessing {
                InstrumentPicker(selected: $selectedInstrument, options: instruments)
                ImportButton(showingFilePicker: $showingFilePicker)
            }
            
            TrainingVisuals(
                targetHistory: targetHistory,
                liveHistory: liveHistory,
                currentTime: currentTime,
                targetPitch: pitchManager.targetPitch,
                livePitch: audioEngine.livePitch,
                accuracy: gradingManager.lastAccuracy,
                score: gradingManager.currentScore
            )
            
            Spacer()
        }
        .padding(40)
        .frame(minWidth: 800, minHeight: 750)
        .fileImporter(
            isPresented: $showingFilePicker,
            allowedContentTypes: [.audio, .mp3, .wav, .mpeg4Audio],
            allowsMultipleSelection: false,
            onCompletion: handleFileImport
        )
        .onReceive(Timer.publish(every: updateInterval, on: .main, in: .common).autoconnect()) { _ in
            updateTrainingState()
        }
    }
    
    private func updateTrainingState() {
        currentTime += updateInterval
        pitchManager.updateTargetPitch(forTime: currentTime)
        gradingManager.gradePitch(live: audioEngine.livePitch, target: pitchManager.targetPitch)
        
        updateHistory()
    }
    
    private func updateHistory() {
        if pitchManager.targetPitch > 0 {
            targetHistory.append(PitchPoint(time: currentTime, frequency: pitchManager.targetPitch))
        }
        if audioEngine.livePitch > 0 {
            liveHistory.append(PitchPoint(time: currentTime, frequency: audioEngine.livePitch))
        }
        
        // Performance optimization: keep history window manageable
        if targetHistory.count > 500 { targetHistory.removeFirst() }
        if liveHistory.count > 500 { liveHistory.removeFirst() }
    }
    
    private func handleFileImport(result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            if let url = urls.first { processFile(at: url) }
        case .failure(let error):
            statusMessage = "Import failed: \(error.localizedDescription)"
        }
    }
    
    private func processFile(at url: URL) {
        isProcessing = true
        targetHistory = []
        liveHistory = []
        currentTime = 0
        
        Task {
            do {
                let instrument = selectedInstrument
                updateStatus("1/3: Separating \(instrument.capitalized)...")
                
                let mode = instrument == "vocals" ? "vocals" : "4-stem"
                let sepResult = try await BackendClient.shared.uploadAndSeparate(fileURL: url, mode: mode)
                
                let stemName = instrument == "vocals" ? "vocals.wav" : "other.wav"
                guard let targetPath = sepResult.output_files.first(where: { $0.contains(stemName) }) else {
                    throw MoosicError.stemNotFound(instrument)
                }
                
                if instrument == "vocals" {
                    updateStatus("2/3: Transcribing Lyrics...")
                    _ = try await BackendClient.shared.transcribeVocals(vocalsPath: targetPath)
                }
                
                updateStatus("3/3: Extracting Pitch...")
                let pitchResult = try await BackendClient.shared.extractPitch(audioPath: targetPath, instrument: instrument)
                
                if let pitchFile = pitchResult.output_files.first {
                    pitchManager.loadPitchData(from: URL(fileURLWithPath: pitchFile))
                }
                
                completeProcessing(message: "\(instrument.capitalized) analysis complete!")
            } catch {
                handleError(error)
            }
        }
    }
    
    private func updateStatus(_ message: String) {
        Task { @MainActor in statusMessage = message }
    }
    
    private func completeProcessing(message: String) {
        Task { @MainActor in
            isProcessing = false
            statusMessage = message
            try? audioEngine.start()
        }
    }
    
    private func handleError(_ error: Error) {
        Task { @MainActor in
            isProcessing = false
            statusMessage = "Error: \(error.localizedDescription)"
        }
    }
}

// MARK: - Components

struct StatusArea: View {
    let message: String
    let isProcessing: Bool
    
    var body: some View {
        VStack(spacing: 8) {
            Text("Moosic").font(.system(size: 32, weight: .black, design: .rounded))
            if isProcessing { ProgressView().padding(.vertical, 4) }
            Text(message).foregroundColor(.secondary).multilineTextAlignment(.center)
        }
    }
}

struct InstrumentPicker: View {
    @Binding var selected: String
    let options: [String]
    
    var body: some View {
        Picker("Training Mode", selection: $selected) {
            ForEach(options, id: \.self) { Text($0.capitalized).tag($0) }
        }
        .pickerStyle(.segmented)
        .frame(maxWidth: 300)
    }
}

struct TrainingVisuals: View {
    let targetHistory: [PitchPoint]
    let liveHistory: [PitchPoint]
    let currentTime: Double
    let targetPitch: Float
    let livePitch: Float
    let accuracy: Double
    let score: Double
    
    var body: some View {
        VStack(spacing: 20) {
            PitchCurveView(targetHistory: targetHistory, liveHistory: liveHistory, currentTime: currentTime)
            PitchVisualizer(targetPitch: targetPitch, livePitch: livePitch, accuracy: accuracy)
            ScoreView(score: score)
        }
    }
}

enum MoosicError: LocalizedError {
    case stemNotFound(String)
    var errorDescription: String? {
        switch self {
        case .stemNotFound(let inst): return "\(inst.capitalized) stem not found in separation output."
        }
    }
}
