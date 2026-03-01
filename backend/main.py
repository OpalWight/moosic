from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import os
import shutil
import subprocess
from typing import List, Optional
import numpy as np
import librosa
import soundfile as sf
import json

# Force torchaudio to use stable FFmpeg/SoX backends
os.environ["TORCHAUDIO_USE_BACKEND_DISPATCHER"] = "1"

# Optional ML Imports
try:
    import torch
    import whisper
    import demucs
    HAS_ML = True
except ImportError:
    HAS_ML = False

# Force HAS_ML to False if running in a known restricted environment
if os.environ.get("MOOSIC_MOCK_ML") == "1":
    HAS_ML = False

app = FastAPI(title="Moosic Backend")

# Global status for transparency
progress_status = {
    "task": "Idle",
    "details": "Waiting for input...",
    "percentage": 0
}

@app.get("/progress")
async def get_progress():
    return progress_status

def update_progress(task: str, details: str, percentage: int = 0):
    global progress_status
    progress_status["task"] = task
    progress_status["details"] = details
    progress_status["percentage"] = percentage
    print(f"[{task}] {details} ({percentage}%)")

# Constants & Directories
BASE_DIR = os.getcwd()
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")
DEVICE = "mps" if HAS_ML and torch.backends.mps.is_available() else "cpu"

for d in [TEMP_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

class ProcessingStatus(BaseModel):
    status: str
    message: str
    output_files: List[str] = []

def get_song_output_dir(filename: str) -> str:
    song_name = os.path.splitext(filename)[0]
    return os.path.join(OUTPUT_DIR, "htdemucs", song_name)

def run_ml_command(command: List[str], task_name: str) -> None:
    """Runs an ML command with detailed error reporting and status updates."""
    update_progress(task_name, "Starting process...")
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            update_progress(task_name, f"Failed: {error_msg[:50]}...")
            if HAS_ML:
                raise HTTPException(status_code=500, detail=f"ML process failed: {error_msg[:200]}")
        update_progress(task_name, "Complete!", 100)
    except FileNotFoundError:
        msg = "Demucs or FFmpeg not found in system PATH."
        update_progress(task_name, "Error: Tool not found")
        if HAS_ML:
            raise HTTPException(status_code=500, detail=msg)
        print("Mock Mode: Continuing without execution.")

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Moosic Local Backend is running"}

@app.post("/separate", response_model=ProcessingStatus)
async def separate_audio(file: UploadFile = File(...), mode: str = "vocals"):
    """Stage 1 & 2: Source Separation using Demucs."""
    try:
        update_progress("Separation", f"Ingesting {file.filename}...", 5)
        input_path = os.path.join(TEMP_DIR, file.filename)
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if HAS_ML and shutil.which("ffmpeg") is None:
            raise HTTPException(status_code=500, detail="FFmpeg is not installed.")

        command = ["python3", "-m", "demucs", "-o", OUTPUT_DIR]
        if mode == "vocals":
            command += ["--two-stems", "vocals"]
        command.append(input_path)
        
        update_progress("Separation", "Running Demucs (this may take a minute)...", 20)
        run_ml_command(command, "Separation")
        
        base_output = get_song_output_dir(file.filename)
        stems = ["vocals.wav"]
        stems += ["no_vocals.wav"] if mode == "vocals" else ["drums.wav", "bass.wav", "other.wav"]
        
        output_files = [os.path.join(base_output, stem) for stem in stems]
        
        if HAS_ML and not any(os.path.exists(f) for f in output_files):
            raise HTTPException(status_code=500, detail="Demucs finished but no output files were found.")

        return ProcessingStatus(
            status="success",
            message=f"Separation complete ({mode}) for {file.filename}.",
            output_files=output_files
        )
    except Exception as e:
        update_progress("Separation", "Failed")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe", response_model=ProcessingStatus)
async def transcribe_vocals(vocals_path: str):
    """Stage 3: Lyric Extraction using Whisper."""
    update_progress("Transcription", "Initializing Whisper...", 10)
    if not HAS_ML or not os.path.exists(vocals_path):
        msg = "Mock transcription." if not HAS_ML else "File not found, using mock."
        update_progress("Transcription", "Complete (Mock)", 100)
        return ProcessingStatus(status="success", message=msg, output_files=["lyrics.json"])

    try:
        update_progress("Transcription", "Loading model and transcribing...", 30)
        model = whisper.load_model("base", device=DEVICE)
        result = model.transcribe(vocals_path, verbose=False)
        
        json_path = vocals_path.replace(".wav", "_lyrics.json")
        with open(json_path, "w") as f:
            json.dump(result, f, indent=4)
            
        update_progress("Transcription", "Complete!", 100)
        return ProcessingStatus(status="success", message="Transcription complete.", output_files=[json_path])
    except Exception as e:
        update_progress("Transcription", "Failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/extract-pitch", response_model=ProcessingStatus)
async def extract_pitch(audio_path: str, instrument: str = "vocals"):
    """Stage 4: Pitch Extraction using librosa.pyin."""
    update_progress("Pitch Extraction", f"Analyzing {instrument}...", 10)
    if not os.path.exists(audio_path):
        update_progress("Pitch Extraction", "Complete (Mock)", 100)
        return ProcessingStatus(status="success", message=f"Mock {instrument} pitch.", output_files=["pitch.json"])

    try:
        update_progress("Pitch Extraction", "Loading audio into memory...", 30)
        y, sr = librosa.load(audio_path, sr=22050)
        update_progress("Pitch Extraction", "Calculating Hz map (pYIN)...", 60)
        f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        
        pitch_data = [float(p) if not np.isnan(p) else 0.0 for p in f0]
        json_path = audio_path.replace(".wav", "_pitch.json")
        
        with open(json_path, "w") as f:
            json.dump({"pitch": pitch_data, "sr": sr, "instrument": instrument}, f)
            
        update_progress("Pitch Extraction", "Complete!", 100)
        return ProcessingStatus(status="success", message=f"Pitch extraction complete for {instrument}.", output_files=[json_path])
    except Exception as e:
        update_progress("Pitch Extraction", "Failed")
        raise HTTPException(status_code=500, detail=f"Pitch extraction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
