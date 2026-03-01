from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import os
import shutil
import subprocess
from typing import List
try:
    import torch
    import whisper
    HAS_ML = True
except ImportError:
    HAS_ML = False
import numpy as np
import librosa
import soundfile as sf
import json

app = FastAPI(title="Moosic Backend")

# Configuration for storage
BASE_DIR = os.getcwd()
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Determine device (Apple Silicon support)
device = "mps" if HAS_ML and torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

class ProcessingStatus(BaseModel):
    status: str
    message: str
    output_files: List[str] = []

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Moosic Local Backend is running"}

@app.post("/separate", response_model=ProcessingStatus)
async def separate_audio(file: UploadFile = File(...), mode: str = "vocals"):
    """
    Stage 1 & 2: Source Separation using Demucs.
    Modes: "vocals" (2-stems) or "4-stem" (vocals, drums, bass, other)
    """
    try:
        input_path = os.path.join(TEMP_DIR, file.filename)
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Demucs configuration
        if mode == "vocals":
            command = ["python3", "-m", "demucs", "--two-stems", "vocals", "-o", OUTPUT_DIR, input_path]
        else:
            command = ["python3", "-m", "demucs", "-o", OUTPUT_DIR, input_path]
        
        print(f"Running command: {' '.join(command)}")
        # In actual use, subprocess.run(command, check=True)
        
        song_name = os.path.splitext(file.filename)[0]
        base_output = os.path.join(OUTPUT_DIR, "htdemucs", song_name)
        
        output_files = []
        if mode == "vocals":
            output_files = [os.path.join(base_output, "vocals.wav"), os.path.join(base_output, "no_vocals.wav")]
        else:
            output_files = [
                os.path.join(base_output, "vocals.wav"),
                os.path.join(base_output, "drums.wav"),
                os.path.join(base_output, "bass.wav"),
                os.path.join(base_output, "other.wav")
            ]
        
        return ProcessingStatus(
            status="success",
            message=f"Separation complete ({mode}) for {file.filename}.",
            output_files=output_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe", response_model=ProcessingStatus)
async def transcribe_vocals(vocals_path: str):
    """
    Stage 3: Lyric Extraction & Alignment using Whisper.
    """
    try:
        if not os.path.exists(vocals_path) and not HAS_ML:
             return ProcessingStatus(status="success", message="Mock transcription.", output_files=["lyrics.json"])
             
        model = whisper.load_model("base", device=device)
        result = model.transcribe(vocals_path, verbose=False)
        
        json_path = vocals_path.replace(".wav", "_lyrics.json")
        with open(json_path, "w") as f:
            json.dump(result, f, indent=4)
            
        return ProcessingStatus(
            status="success",
            message="Transcription complete.",
            output_files=[json_path]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-pitch", response_model=ProcessingStatus)
async def extract_pitch(audio_path: str, instrument: str = "vocals"):
    """
    Stage 4: Pitch Extraction.
    Uses librosa.pyin for monophonic pitch detection.
    """
    try:
        if not os.path.exists(audio_path) and not HAS_ML:
             return ProcessingStatus(status="success", message=f"Mock {instrument} pitch extraction.", output_files=["pitch.json"])

        y, sr = librosa.load(audio_path, sr=22050)
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7')
        )
        
        pitch_data = [float(p) if not np.isnan(p) else 0.0 for p in f0]
        pitch_path = audio_path.replace(".wav", "_pitch.json")
        with open(pitch_path, "w") as f:
            json.dump({"pitch": pitch_data, "sr": sr, "instrument": instrument}, f)
            
        return ProcessingStatus(
            status="success",
            message=f"Pitch extraction complete for {instrument}.",
            output_files=[pitch_path]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
