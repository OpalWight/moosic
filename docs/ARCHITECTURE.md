# VocalizeNative Architecture

## 1. System Overview
VocalizeNative is a decoupled architecture consisting of a **macOS Native Frontend (SwiftUI)** and an **Embedded Python Backend (FastAPI)**.

## 2. High-Level Diagram
```text
[ User Interface (SwiftUI) ] <--> [ Backend Client (Swift) ] <--> [ FastAPI Server (Python) ]
             |                                                          |
             | (Real-time Audio)                                        | (Heavy ML)
             v                                                          v
[ AudioEngine (AVFoundation) ]                              [ ML Models (Demucs/Whisper) ]
[ FFT Engine (Accelerate) ]                                 [ Pitch Map (Librosa) ]
```

## 3. Data Flow
### 3.1 Initial Import (The "Cold" Path)
1. **User** selects a file and instrument (vocals, piano, guitar) in SwiftUI.
2. **Swift** sends the file and instrument to the local Python server via `POST /process?instrument={type}`.
3. **Python (Demucs)** splits the file into stems and saves them in `output_files/{song_name}_{instrument}/`.
4. **Python (Whisper)** transcribes `vocals.wav` into `lyrics.json` (if instrument is vocals).
5. **Python (Librosa)** extracts pitch into `pitch.json` for the target instrument.
6. **Swift** receives a single JSON response containing URLs to all generated assets.

### 3.2 Live Training (The "Hot" Path)
1. **Swift (AVAudioEngine)** plays the backing track (`backing.wav`).
2. **Swift (AVAudioEngine)** captures live microphone input.
3. **Swift (Accelerate)** performs a Fast Fourier Transform (FFT) every ~20ms on the mic buffer to determine the current frequency (Hz).
4. **Grading Logic** compares the live frequency against the corresponding timestamp in `pitch.json`.
5. **UI** updates the scrolling "pitch bars" and "rolling lyrics" at 60fps.

## 4. Technology Selection Rationale
- **FastAPI**: Lightweight, fast, and easy to bundle as a single binary.
- **AVFoundation**: Low-latency native audio capture and playback.
- **Accelerate Framework**: High-performance vector processing on Apple Silicon, essential for low-latency FFT.
- **MPS (Metal Performance Shaders)**: Utilizes the Mac's GPU for ML inference (Demucs/Whisper) without taxing the CPU.

## 5. Security & Isolation
- **Network**: Bound strictly to `127.0.0.1`. No external traffic.
- **Sandbox**: Utilizes macOS App Sandboxing with `com.apple.security.assets` and `com.apple.security.device.microphone` entitlements.
