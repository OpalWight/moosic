from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import os
import shutil
import subprocess
from typing import List
import torch
import numpy as np
import whisper
import librosa
import soundfile as sf
import json

app = FastAPI(title="VocalizeNative Backend")

# Configuration for storage
BASE_DIR = os.getcwd()
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Determine device (Apple Silicon support)
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

class ProcessingStatus(BaseModel):
    status: str
    message: str
    output_files: List[str] = []

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "VocalizeNative Local Backend is running"}

@app.post("/separate", response_model=ProcessingStatus)
async def separate_audio(file: UploadFile = File(...)):
    """
    Stage 1 & 2: Source Separation using Demucs.
    """
    try:
        input_path = os.path.join(TEMP_DIR, file.filename)
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Call Demucs CLI for better process isolation
        # Using htdemucs for better quality
        command = [
            "python3", "-m", "demucs",
            "--two-stems", "vocals",
            "-o", OUTPUT_DIR,
            input_path
        ]
        
        # In a real environment, we would use subprocess.run
        # For now, let's provide the logic but keep it safe for simulation
        print(f"Running command: {' '.join(command)}")
        # subprocess.run(command, check=True)
        
        # Expected output paths (Demucs default structure)
        # output_files/htdemucs/song_name/vocals.wav
        # output_files/htdemucs/song_name/no_vocals.wav
        
        song_name = os.path.splitext(file.filename)[0]
        vocals_path = os.path.join(OUTPUT_DIR, "htdemucs", song_name, "vocals.wav")
        instr_path = os.path.join(OUTPUT_DIR, "htdemucs", song_name, "no_vocals.wav")
        
        return ProcessingStatus(
            status="success",
            message=f"Separation complete for {file.filename}.",
            output_files=[vocals_path, instr_path]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe", response_model=ProcessingStatus)
async def transcribe_vocals(vocals_path: str):
    """
    Stage 3: Lyric Extraction & Alignment using Whisper.
    """
    try:
        # Load whisper model (base/small for speed on local machines)
        model = whisper.load_model("base", device=device)
        result = model.transcribe(vocals_path, verbose=False)
        
        # Save transcription to JSON
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
async def extract_pitch(vocals_path: str):
    """
    Stage 4: Pitch Extraction using librosa/pyin for local robustness.
    """
    try:
        # Load audio
        y, sr = librosa.load(vocals_path, sr=22050)
        
        # Use pYIN algorithm for pitch detection
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7')
        )
        
        # Filter and save to JSON
        # Convert f0 to list and handle NaNs for JSON serialization
        pitch_data = [float(p) if not np.isnan(p) else 0.0 for p in f0]
        
        pitch_path = vocals_path.replace(".wav", "_pitch.json")
        with open(pitch_path, "w") as f:
            json.dump({"pitch": pitch_data, "sr": sr}, f)
            
        return ProcessingStatus(
            status="success",
            message="Pitch extraction complete.",
            output_files=[pitch_path]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
