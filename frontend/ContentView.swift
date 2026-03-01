import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @State private var isProcessing = false
    @State private var statusMessage = "Welcome to VocalizeNative"
    @State private var showingFilePicker = false
    
    var body: some View {
        VStack(spacing: 20) {
            Text("VocalizeNative")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            if isProcessing {
                ProgressView("Analyzing your song...")
            } else {
                Button(action: { showingFilePicker = true }) {
                    Label("Import Audio File", systemImage: "music.note.list")
                        .padding()
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
            
            Text(statusMessage)
                .foregroundColor(.secondary)
            
            Spacer()
            
            // Placeholder for real-time training UI
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.gray.opacity(0.1))
                .overlay(
                    Text("Lyrics and Pitch Bars will appear here")
                        .foregroundColor(.gray)
                )
                .frame(height: 300)
        }
        .padding(40)
        .frame(minWidth: 600, minHeight: 500)
        .fileImporter(
            isPresented: $showingFilePicker,
            allowedContentTypes: [.audio, .mp3, .wav, .mpeg4Audio],
            allowsMultipleSelection: false
        ) { result in
            handleFileImport(result: result)
        }
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
                // Stage 1: Separate
                let sepResult = try await BackendClient.shared.uploadAndSeparate(fileURL: url)
                guard let vocalsPath = sepResult.output_files.first(where: { $0.contains("vocals.wav") }) else {
                    throw NSError(domain: "VocalizeNative", code: 1, userInfo: [NSLocalizedDescriptionKey: "Vocals not found"])
                }
                
                // Stage 2: Transcribe
                await MainActor.run { statusMessage = "2/3: Transcribing Lyrics..." }
                let transResult = try await BackendClient.shared.transcribeVocals(vocalsPath: vocalsPath)
                
                // Stage 3: Pitch
                await MainActor.run { statusMessage = "3/3: Extracting Pitch..." }
                let pitchResult = try await BackendClient.shared.extractPitch(vocalsPath: vocalsPath)
                
                await MainActor.run {
                    isProcessing = false
                    statusMessage = "Analysis complete! Ready to sing."
                    // Here we would load the data into the AudioEngine and UI
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

#Preview {
    ContentView()
}
