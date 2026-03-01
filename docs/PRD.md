# Product Requirements Document (PRD): VocalizeNative

## 1. Executive Summary
**VocalizeNative** is a local, open-source macOS application designed for private, high-performance vocal training. It enables users to securely import their own audio files and perform real-time vocal analysis and grading entirely on-device, ensuring zero latency and absolute data privacy.

## 2. Problem Statement
Many vocal training apps require cloud-based processing for source separation and transcription, raising privacy concerns and introducing network-dependent latency. Existing local solutions are often complex to set up for non-technical users.

## 3. Goals & Objectives
- **Local-First ML:** Perform source separation (vocals/instrumentals), lyric alignment, and pitch extraction using the Mac's GPU (MPS).
- **Zero-Latency Feedback:** Provide real-time pitch grading with minimal audio round-trip delay.
- **Privacy by Design:** No internet connection required. No data transmission.
- **Seamless UX:** A polished, native macOS experience using SwiftUI.

## 4. Target Audience
- Vocalists and hobbyist singers seeking private practice.
- Music students and teachers.
- Privacy-conscious performers who want to train with their own library.

## 5. Functional Requirements

### 5.1 Local File Ingestion
- Support for MP3, WAV, and M4A.
- Drag-and-drop or native file picker.
- Secure temporary staging of files in `NSTemporaryDirectory()`.

### 5.2 Processing Pipeline (Python Backend)
- **Source Separation:** Using Meta's `HTDemucs` (MPS-optimized).
- **Transcription & Alignment:** Using `WhisperX` for precise word-level timestamps.
- **Pitch Extraction:** Using `CREPE` or `basic-pitch` for high-resolution frequency data.
- **Communication:** Swift communicates with a local FastAPI server via JSON over localhost.

### 5.3 Real-Time Training Interface (Swift Frontend)
- **Visuals:** Scrolling lyrics, scrolling pitch bars (target vs. live).
- **Audio Control:** Play/Pause, Volume (independent for backing and vocals), Metronome.
- **Live Feedback:** Real-time note detection and accuracy scoring using `Accelerate` (FFT).
- **Recording:** Option to record sessions locally for review.

## 6. Technical Specifications

### 6.1 Frontend (macOS Native)
- **Framework:** SwiftUI.
- **Audio Engine:** `AVFoundation` (`AVAudioEngine`, `AVAudioNode`).
- **Data Flow:** `Combine` or `Observation` for real-time UI updates.
- **Pitch Detection:** FFT-based (Accelerate framework) for live feedback.

### 6.2 Backend (Embedded Python)
- **Runtime:** Python 3.10+ bundled via PyInstaller.
- **API Framework:** FastAPI (local only).
- **ML Frameworks:** PyTorch (with MPS support), WhisperX, demucs, crepe.

### 6.3 Packaging & Distribution
- **Build Tool:** Xcode + Python bundling script.
- **Distribution:** Signed and notarized `.dmg` or `.app` via GitHub Releases.

## 7. Security & Privacy
- **No Internet Access:** The app will not request `com.apple.security.network.client` or `com.apple.security.network.server` entitlements for external access.
- **Local Data Only:** All models are downloaded once during installation/first-run (if not bundled) and used offline.
- **File Security:** Temporary files are cleared upon app exit.

## 8. Performance Targets
- **Inference Speed:** Source separation for a 3-minute song should take < 45 seconds on M1 Base.
- **UI Responsiveness:** 60fps for scrolling visuals.
- **Audio Latency:** < 10ms for live monitoring.

## 9. Future Roadmap
- Multi-track support.
- Collaborative offline sessions (Local Network).
- Vocal health monitoring (Detecting strain).
