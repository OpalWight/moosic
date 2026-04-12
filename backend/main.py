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
import scipy.signal
from urllib.parse import quote

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp_files")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_files")

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
    assets: Dict[str, str]

def run_cmd(cmd: List[str], task: str):
    """Internal helper for ML commands."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and HAS_ML:
            raise Exception(f"{task} failed: {res.stderr[:200]}")
    except FileNotFoundError:
        if HAS_ML: raise Exception(f"{task} tool not found")

def extract_polyphonic_pitches(y, sr, n_notes=3):
    """Extract multiple pitches per frame using CQT and peak detection."""
    hop_length = 512
    C = np.abs(librosa.cqt(y, sr=sr, hop_length=hop_length, n_bins=84, bins_per_octave=12))
    
    # Noise threshold
    C[C < np.max(C) * 0.1] = 0
    
    points = []
    for i, frame in enumerate(C.T):
        time = float(i * hop_length) / float(sr)
        peaks, _ = scipy.signal.find_peaks(frame, height=np.max(frame) * 0.15 if np.max(frame) > 0 else 1.0)
        
        # Sort peaks by energy and pick top n
        top_peaks = peaks[np.argsort(frame[peaks])[-n_notes:]]
        for p in top_peaks:
            # bin 0 is C1
            freq = float(librosa.midi_to_hz(p + 24)) 
            points.append({"t": time, "f": freq})
    return points

def extract_chords(y, sr):
    """Identify chords using chroma template matching."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    
    templates = []
    chord_names = []
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    for i in range(12):
        # Major
        maj = np.zeros(12); maj[[i, (i+4)%12, (i+7)%12]] = 1
        templates.append(maj); chord_names.append(f"{notes[i]}")
        # Minor
        min = np.zeros(12); min[[i, (i+3)%12, (i+7)%12]] = 1
        templates.append(min); chord_names.append(f"{notes[i]}m")
    
    templates = np.array(templates)
    chords = []
    for i, frame in enumerate(chroma.T):
        time = float(i * 512) / float(sr)
        if np.max(frame) < 0.1: continue
        
        corrs = np.dot(templates, frame)
        best_idx = np.argmax(corrs)
        if corrs[best_idx] > 0.6:
            chords.append({"t": time, "name": chord_names[best_idx]})
    return chords

@app.get("/")
async def health_check():
    return {"status": "ok", "ml_enabled": HAS_ML, "device": DEVICE}

@app.get("/progress")
async def get_progress():
    return progress.status

@app.post("/process", response_model=ProcessResult)
def process_audio(file: UploadFile = File(...)):
    """Unified pipeline: 4-Stem Separation -> Transcription -> Specialized Pitch Extraction."""
    song_basename = os.path.splitext(file.filename)[0]
    project_name = song_basename
    project_dir = os.path.join(OUTPUT_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)

    input_path = os.path.join(TEMP_DIR, file.filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Separation (Always 4 stems)
        progress.update("Separation", "Splitting audio stems...", 10)
        sep_cmd = ["python3", "-m", "demucs", "-o", TEMP_DIR, input_path]
        run_cmd(sep_cmd, "Separation")

        # Move stems
        demucs_out = os.path.join(TEMP_DIR, "htdemucs", song_basename)
        assets = {}
        for stem in ["vocals", "drums", "bass", "other", "no_vocals"]:
            src = os.path.join(demucs_out, f"{stem}.wav")
            dst = os.path.join(project_dir, f"{stem}.wav")
            if os.path.exists(src):
                shutil.move(src, dst)
                # Map 'other' to 'guitar' for frontend
                asset_key = "guitar" if stem == "other" else ("backing" if stem == "no_vocals" else stem)
                assets[asset_key] = f"/output/{quote(project_name)}/{stem}.wav"

        # 2. Transcription
        vocal_path = os.path.join(project_dir, "vocals.wav")
        if os.path.exists(vocal_path):
            progress.update("Transcription", "Extracting lyrics...", 50)
            if HAS_ML:
                model = whisper.load_model("base", device=DEVICE)
                res = model.transcribe(vocal_path)
                with open(os.path.join(project_dir, "lyrics.json"), "w") as f:
                    json.dump(res, f, indent=4)
            else:
                with open(os.path.join(project_dir, "lyrics.json"), "w") as f:
                    json.dump({"segments": [{"text": "Mock lyrics", "start": 0, "end": 10}]}, f)
            assets["lyrics"] = f"/output/{quote(project_name)}/lyrics.json"

        # 3. Multi-Pitch Extraction
        progress.update("Pitch", "Analyzing pitch for all instruments...", 70)
        for stem in ["vocals", "bass", "guitar"]: # Renamed 'other' to 'guitar' logic-wise below
            stem_filename = "other" if stem == "guitar" else stem
            stem_path = os.path.join(project_dir, f"{stem_filename}.wav")
            
            if os.path.exists(stem_path):
                pitch_filename = f"{stem}_pitch.json"
                if HAS_ML:
                    y, sr = librosa.load(stem_path, sr=22050)
                    if stem == "guitar":
                        progress.update("Pitch", "Specialized guitar chord analysis...", 75)
                        points = extract_polyphonic_pitches(y, sr)
                        chords = extract_chords(y, sr)
                        with open(os.path.join(project_dir, pitch_filename), "w") as f:
                            json.dump({"points": points, "chords": chords, "sr": sr, "type": "polyphonic"}, f)
                    else:
                        f0, _, probs = librosa.pyin(y, fmin=librosa.note_to_hz('C1' if stem == 'bass' else 'C2'), 
                                                   fmax=librosa.note_to_hz('C5' if stem == 'bass' else 'C7'), sr=sr)
                        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
                        if len(rms) > 0 and np.max(rms) > 0: rms = rms / np.max(rms)
                        
                        # Save RAW values for real-time filtering in Swift
                        raw_f0 = [float(p) if not np.isnan(p) else 0.0 for p in f0]
                        raw_probs = [float(p) for p in probs]
                        raw_rms = [float(r) for r in rms]
                        
                        with open(os.path.join(project_dir, pitch_filename), "w") as f:
                            json.dump({
                                "raw_f0": raw_f0,
                                "raw_probs": raw_probs,
                                "raw_rms": raw_rms,
                                "sr": sr, 
                                "type": "monophonic"
                            }, f)
                else:
                    with open(os.path.join(project_dir, pitch_filename), "w") as f:
                        json.dump({"pitch": [0, 0, 0], "sr": 22050, "type": "monophonic"}, f)
                assets[f"{stem}_pitch"] = f"/output/{quote(project_name)}/{pitch_filename}"

        progress.update("Complete", "Song ready!", 100)
        return ProcessResult(status="success", song_name=song_basename, assets=assets)
    except Exception as e:
        progress.update("Failed", str(e), 0)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/songs")
async def list_songs():
    songs = []
    if not os.path.exists(OUTPUT_DIR): return []
    for project_name in os.listdir(OUTPUT_DIR):
        p_path = os.path.join(OUTPUT_DIR, project_name)
        if not os.path.isdir(p_path): continue
        files = os.listdir(p_path)
        if not any(f.endswith(".wav") for f in files): continue
        
        assets = {}
        for f in files:
            name_parts = f.split(".")
            if len(name_parts) < 2: continue
            base_name = name_parts[0]
            ext = name_parts[-1]
            
            # Map 'other' to 'guitar' for frontend compatibility
            key = base_name
            if key == "other":
                key = "guitar"
            if key == "no_vocals":
                key = "backing"
            # Note: other_pitch.json should stay as other_pitch if generated that way, 
            # but the process_audio function uses f"{stem}_pitch.json" where stem is "guitar"
            # so it actually saves as "guitar_pitch.json".
            # However, existing files might have "other_pitch.json".
            if key == "other_pitch":
                key = "guitar_pitch"
                
            assets[key] = f"/output/{quote(project_name)}/{f}"
            
        songs.append({"id": project_name, "name": project_name, "assets": assets})
    return songs

@app.delete("/songs/{project_id}")
async def delete_song(project_id: str):
    abs_output_dir = os.path.abspath(OUTPUT_DIR)
    project_dir = os.path.abspath(os.path.join(abs_output_dir, project_id))
    if not project_dir.startswith(abs_output_dir): raise HTTPException(status_code=403, detail="Invalid project ID")
    if os.path.exists(project_dir) and os.path.isdir(project_dir):
        shutil.rmtree(project_dir); return {"status": "success"}
    raise HTTPException(status_code=404, detail="Project not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
