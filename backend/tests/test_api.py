from fastapi.testclient import TestClient
import os
import io
from VocalizeNative.backend.main import app

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
    
    response = client.post("/separate", files=files)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "vocals.wav" in response.json()["output_files"]

def test_transcribe_endpoint():
    response = client.post("/transcribe?filename=vocals.wav")
    assert response.status_code == 200
    assert "lyrics.json" in response.json()["output_files"]

def test_extract_pitch_endpoint():
    response = client.post("/extract-pitch?filename=vocals.wav")
    assert response.status_code == 200
    assert "pitch_data.json" in response.json()["output_files"]
