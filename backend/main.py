from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import shutil
import subprocess
from typing import List, Dict, Optional
import numpy as np
import librosa
import json
from urllib.parse import quote

# Configuration
BASE_DIR = os.getcwd()
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_files")

for d in [TEMP_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

os.environ["TORCHAUDIO_USE_BACKEND_DISPATCHER"] = "1"

try:
    import torch
    import whisper
    HAS_ML = os.environ.get("MOOSIC_MOCK_ML") != "1"
    DEVICE = "mps" if HAS_ML and torch.backends.mps.is_available() else "cpu"
except ImportError:
    HAS_ML = False
    DEVICE = "cpu"

app = FastAPI(title="Moosic Backend")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

class ProgressManager:
    def __init__(self):
        self.status = {"task": "Idle", "details": "Waiting...", "percentage": 0}

    def update(self, task: str, details: str, percentage: int):
        self.status = {"task": task, "details": details, "percentage": percentage}
        print(f"[{task}] {details} ({percentage}%)")

progress = ProgressManager()

class ProcessResult(BaseModel):
    status: str
    song_name: str
    instrument: str
    assets: Dict[str, str]

def run_cmd(cmd: List[str], task: str):
    """Internal helper for ML commands."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and HAS_ML:
            raise Exception(f"{task} failed: {res.stderr[:200]}")
    except FileNotFoundError:
        if HAS_ML: raise Exception(f"{task} tool not found")

@app.get("/")
async def health_check():
    return {"status": "ok", "ml_enabled": HAS_ML, "device": DEVICE}

@app.get("/progress")
async def get_progress():
    return progress.status

@app.post("/process", response_model=ProcessResult)
async def process_audio(file: UploadFile = File(...), instrument: str = "vocals"):
    """Unified pipeline: Separation -> Transcription -> Pitch Extraction."""
    song_basename = os.path.splitext(file.filename)[0]
    # Collision avoidance: separate folder per instrument
    project_name = f"{song_basename}_{instrument}"
    project_dir = os.path.join(OUTPUT_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)

    input_path = os.path.join(TEMP_DIR, file.filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Separation
        progress.update("Separation", "Splitting audio stems...", 10)
        mode = "vocals" if instrument == "vocals" else "4-stem"
        sep_cmd = ["python3", "-m", "demucs", "-o", TEMP_DIR]
        if mode == "vocals": sep_cmd += ["--two-stems", "vocals"]
        sep_cmd.append(input_path)
        run_cmd(sep_cmd, "Separation")

        # Move stems to project directory
        demucs_out = os.path.join(TEMP_DIR, "htdemucs", song_basename)
        stems_map = {
            "vocals": "vocals.wav",
            "backing": "no_vocals.wav" if mode == "vocals" else "other.wav"
        }
        
        for key, stem_file in stems_map.items():
            src = os.path.join(demucs_out, stem_file)
            dst = os.path.join(project_dir, f"{key}.wav")
            if os.path.exists(src):
                shutil.move(src, dst)
            elif not HAS_ML: # Mock file for testing
                with open(dst, "w") as f: f.write("mock audio")

        # 2. Transcription (Vocals only)
        assets = {
            "vocals": f"/output/{quote(project_name)}/vocals.wav",
            "backing": f"/output/{quote(project_name)}/backing.wav"
        }

        if instrument == "vocals":
            progress.update("Transcription", "Extracting lyrics...", 50)
            vocal_path = os.path.join(project_dir, "vocals.wav")
            if HAS_ML and os.path.exists(vocal_path):
                model = whisper.load_model("base", device=DEVICE)
                res = model.transcribe(vocal_path)
                with open(os.path.join(project_dir, "lyrics.json"), "w") as f:
                    json.dump(res, f, indent=4)
            else:
                with open(os.path.join(project_dir, "lyrics.json"), "w") as f:
                    json.dump({"text": "Mock lyrics"}, f)
            assets["lyrics"] = f"/output/{quote(project_name)}/lyrics.json"

        # 3. Pitch Extraction
        progress.update("Pitch", "Analyzing target pitch...", 80)
        target_path = os.path.join(project_dir, "vocals.wav")
        if os.path.exists(target_path) and HAS_ML:
            y, sr = librosa.load(target_path, sr=22050)
            f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
            pitch_data = [float(p) if not np.isnan(p) else 0.0 for p in f0]
            with open(os.path.join(project_dir, "pitch.json"), "w") as f:
                json.dump({"pitch": pitch_data, "sr": sr, "instrument": instrument}, f)
        else:
            with open(os.path.join(project_dir, "pitch.json"), "w") as f:
                json.dump({"pitch": [0, 0, 0], "sr": 22050, "instrument": instrument}, f)
        
        assets["pitch"] = f"/output/{quote(project_name)}/pitch.json"
        
        progress.update("Complete", "Song ready!", 100)
        return ProcessResult(
            status="success",
            song_name=song_basename,
            instrument=instrument,
            assets=assets
        )

    except Exception as e:
        progress.update("Failed", str(e), 0)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/songs")
async def list_songs():
    """List processed projects."""
    songs = []
    for project_name in os.listdir(OUTPUT_DIR):
        p_path = os.path.join(OUTPUT_DIR, project_name)
        if not os.path.isdir(p_path): continue
        
        files = os.listdir(p_path)
        if "vocals.wav" not in files: continue
        
        # Infer instrument from folder name suffix
        parts = project_name.rsplit("_", 1)
        name = parts[0]
        instrument = parts[1] if len(parts) > 1 else "vocals"
        
        songs.append({
            "id": project_name,
            "name": name,
            "instrument": instrument,
            "assets": { f.split(".")[0]: f"/output/{quote(project_name)}/{f}" for f in files }
        })
    return songs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


