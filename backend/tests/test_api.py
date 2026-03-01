from fastapi.testclient import TestClient
import os
import io
from moosic.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_separate_endpoint():
    # Mock an audio file upload
    file_content = b"fake audio data"
    file_name = "test_song.wav"
    files = {"file": (file_name, io.BytesIO(file_content), "audio/wav")}
    
    response = client.post("/separate?mode=vocals", files=files)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert any("vocals.wav" in f for f in response.json()["output_files"])

def test_transcribe_endpoint():
    response = client.post("/transcribe?vocals_path=vocals.wav")
    assert response.status_code == 200
    assert any("lyrics.json" in f for f in response.json()["output_files"])

def test_extract_pitch_endpoint():
    # Parameter name is now 'audio_path'
    response = client.post("/extract-pitch?audio_path=vocals.wav&instrument=vocals")
    assert response.status_code == 200
    assert any("pitch.json" in f for f in response.json()["output_files"])
