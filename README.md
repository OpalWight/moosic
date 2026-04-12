# Moosic: Vocal Training

Moosic is an open-source macOS app for vocal training. It uses advanced Machine Learning to analyze songs and provide real-time feedback on your singing performance.

## Features

- **Source Separation**: Automatically split any song (MP3, WAV, M4A) into high-quality vocals and instrumentals using Meta's Demucs.
- **Smart Transcription**: Lyric extraction with word-level timestamps via OpenAI's Whisper.
- **High-Precision Pitch Tracking**: Real-time Hz analysis using the Apple Accelerate framework for zero-latency feedback.
- **Interactive Grading**: Get real-time accuracy scores and visual feedback on your pitch.

## Getting Started

### Prerequisites
- **macOS 14 (Sonoma)** or newer.
- **Apple Silicon (M1, M2, M3, M4)** highly recommended for ML performance.
- **Python 3.10+** installed on your system.

### Installation (Developer Preview)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/moosic.git
   cd moosic
   ```

2. **Set up the Backend**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Backend**:
   ```bash
   python3 main.py
   ```

4. **Launch the Frontend**:
   Open `moosic/Moosic/Moosic.xcodeproj` in Xcode.
   - Run the project.

## Architecture

```text
+-------------------------------------------------+
|                  Moosic App (macOS)             |
|  +-------------------------------------------+  |
|  |               SwiftUI View                |  |
|  +-------------------------------------------+  |
|        |                  |                     |
|  +-----v---------+  +-----v-------------------+ |
|  | BackendClient |  | AudioEngineManager      | |
|  | (API Comms)   |  | (AVAudioEngine + vDSP)  | |
|  +---------------+  +-------------------------+ |
+--------|------------------|---------------------+
         |                  |
         | HTTP / JSON      | Real-time Input
         |                  v
+--------v----------------------------------------+
|                Moosic Backend (Python)          |
|  +-------------------------------------------+  |
|  |              FastAPI Server               |  |
|  +-------------------------------------------+  |
|        |                  |                |    |
|  +-----v---------+  +-----v---------+ +----v---+|
|  | Demucs (AI)   |  | Whisper (AI)  | | librosa| |
|  | (Source Sep)  |  | (Lyrics)      | | (Pitch)| |
|  +---------------+  +---------------+ +--------+|
+-------------------------------------------------+
```

## How It Works

1. **Import**: Drag and drop your audio file.
2. **Analyze**: The Python server separates stems, transcribes lyrics, and maps the target pitch.
3. **Sing**: The app plays the instrumental track while tracking your voice through the microphone.
4. **Learn**: Follow the visual pitch bars and improve your accuracy with real-time scoring.

## License
Open-source under the MIT License.
