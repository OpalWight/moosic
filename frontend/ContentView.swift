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
    
    var body: some View {
        VStack(spacing: 20) {
            HeaderView(statusMessage: statusMessage, isProcessing: isProcessing)
            
            if !isProcessing {
                ImportButton(showingFilePicker: $showingFilePicker)
            }
            
            PitchVisualizer(targetPitch: pitchManager.targetPitch, livePitch: audioEngine.livePitch, accuracy: gradingManager.lastAccuracy)
            
            ScoreView(score: gradingManager.currentScore)
            
            Spacer()
        }
        .padding(40)
        .frame(minWidth: 800, minHeight: 600)
        .fileImporter(
            isPresented: $showingFilePicker,
            allowedContentTypes: [.audio, .mp3, .wav, .mpeg4Audio],
            allowsMultipleSelection: false
        ) { result in
            handleFileImport(result: result)
        }
        .onReceive(Timer.publish(every: 0.05, on: .main, in: .common).autoconnect()) { _ in
            updateTrainingState()
        }
    }
    
    private func updateTrainingState() {
        // In a real app, this would get the actual playback time from the player
        currentTime += 0.05
        pitchManager.updateTargetPitch(forTime: currentTime)
        gradingManager.gradePitch(live: audioEngine.livePitch, target: pitchManager.targetPitch)
    }
    
    private func handleFileImport(result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            processFile(at: url)
        case .failure(let error):
            statusMessage = "Error: \(error.localizedDescription)"
        }
    }
    
    private func processFile(at url: URL) {
        isProcessing = true
        statusMessage = "1/3: Separating Vocals..."
        
        Task {
            do {
                let sepResult = try await BackendClient.shared.uploadAndSeparate(fileURL: url)
                guard let vocalsPath = sepResult.output_files.first(where: { $0.contains("vocals.wav") }) else {
                    throw NSError(domain: "Moosic", code: 1, userInfo: [NSLocalizedDescriptionKey: "Vocals not found"])
                }
                
                await MainActor.run { statusMessage = "2/3: Transcribing Lyrics..." }
                _ = try await BackendClient.shared.transcribeVocals(vocalsPath: vocalsPath)
                
                await MainActor.run { statusMessage = "3/3: Extracting Pitch..." }
                let pitchResult = try await BackendClient.shared.extractPitch(vocalsPath: vocalsPath)
                
                // For simulation, let's assume local access to output files
                if let pitchFile = pitchResult.output_files.first {
                    pitchManager.loadPitchData(from: URL(fileURLWithPath: pitchFile))
                }
                
                await MainActor.run {
                    isProcessing = false
                    statusMessage = "Analysis complete! Ready to sing."
                    try? audioEngine.start()
                }
            } catch {
                await MainActor.run {
                    isProcessing = false
                    statusMessage = "Error: \(error.localizedDescription)"
                }
            }
        }
    }
}

// MARK: - Subviews
struct HeaderView: View {
    let statusMessage: String
    let isProcessing: Bool
    
    var body: some View {
        VStack {
            Text("Moosic")
                .font(.system(size: 32, weight: .black, design: .rounded))
            if isProcessing {
                ProgressView()
                    .padding()
            }
            Text(statusMessage)
                .foregroundColor(.secondary)
        }
    }
}

struct ImportButton: View {
    @Binding var showingFilePicker: Bool
    
    var body: some View {
        Button(action: { showingFilePicker = true }) {
            Label("Import Audio File", systemImage: "music.note.list")
                .font(.headline)
                .padding()
                .frame(maxWidth: 300)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
    }
}

struct PitchVisualizer: View {
    let targetPitch: Float
    let livePitch: Float
    let accuracy: Double
    
    var body: some View {
        HStack(spacing: 40) {
            PitchBar(label: "Target", frequency: targetPitch, color: .blue)
            PitchBar(label: "Live", frequency: livePitch, color: accuracy > 0.5 ? .green : .red)
        }
        .frame(height: 250)
        .padding()
        .background(Color.black.opacity(0.05))
        .cornerRadius(20)
    }
}

struct PitchBar: View {
    let label: String
    let frequency: Float
    let color: Color
    
    var body: some View {
        VStack {
            Text(label).font(.caption).bold()
            ZStack(alignment: .bottom) {
                Capsule().fill(Color.gray.opacity(0.1))
                Capsule()
                    .fill(color)
                    .frame(height: CGFloat(min(frequency / 10, 200))) // Simple normalization
                    .animation(.spring(), value: frequency)
            }
            .frame(width: 40)
            Text("\(Int(frequency)) Hz").font(.caption2).monospacedDigit()
        }
    }
}

struct ScoreView: View {
    let score: Double
    
    var body: some View {
        HStack {
            Image(systemName: "star.fill").foregroundColor(.yellow)
            Text("Score: \(Int(score))")
                .font(.title2)
                .bold()
        }
        .padding()
        .background(Capsule().fill(Color.white).shadow(radius: 2))
    }
}

#Preview {
    ContentView()
}
