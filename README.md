# 🐮 Moosic: Local & Private Vocal Training

**Moosic** is a completely local, open-source macOS app for vocal training. It uses advanced Machine Learning to analyze your favorite songs and provide real-time feedback on your singing performance—all without ever sending your data to the cloud.

## ✨ Features

- **Local Source Separation**: Automatically split any song (MP3, WAV, M4A) into high-quality vocals and instrumentals using Meta's Demucs.
- **Smart Transcription**: Local lyric extraction with word-level timestamps via OpenAI's Whisper.
- **High-Precision Pitch Tracking**: Real-time Hz analysis using the Apple Accelerate framework for zero-latency feedback.
- **Privacy First**: No internet connection required after initial setup. Your recordings and files stay on your Mac.
- **Interactive Grading**: Get real-time accuracy scores and visual feedback on your pitch.

## 🚀 Getting Started

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
   Open `moosic/frontend/VocalizeNativeApp.swift` in Xcode and run the project.

## 🛠 How It Works

1. **Import**: Drag and drop your audio file.
2. **Analyze**: The local Python server separates stems, transcribes lyrics, and maps the target pitch.
3. **Sing**: The app plays the instrumental track while tracking your voice through the microphone.
4. **Learn**: Follow the visual pitch bars and improve your accuracy with real-time scoring.

## 🔒 Privacy Guarantee
Moosic is designed to be incapable of transmitting your files. It binds its internal server to `localhost` and does not request external network entitlements.

## 📜 License
Open-source under the MIT License.
