import os
import io
import json
import pytest

# Set mock mode BEFORE importing app
os.environ["MOOSIC_MOCK_ML"] = "1"

from fastapi.testclient import TestClient
from main import app, ProgressManager

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ml_enabled"] is False

def test_progress_endpoint():
    response = client.get("/progress")
    assert response.status_code == 200
    assert "task" in response.json()
    assert "percentage" in response.json()

def test_unified_process_endpoint():
    # Mock an audio file upload
    file_content = b"fake audio data"
    file_name = "test_song.wav"
    files = {"file": (file_name, io.BytesIO(file_content), "audio/wav")}
    
    response = client.post("/process?instrument=vocals", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["song_name"] == "test_song"
    assert data["instrument"] == "vocals"
    assert "vocals" in data["assets"]
    assert "backing" in data["assets"]
    assert "lyrics" in data["assets"]
    assert "pitch" in data["assets"]

def test_list_songs_endpoint():
    # First ensure a song is processed
    file_content = b"fake audio data"
    file_name = "test_song_2.wav"
    files = {"file": (file_name, io.BytesIO(file_content), "audio/wav")}
    client.post("/process?instrument=guitar", files=files)
    
    response = client.get("/songs")
    assert response.status_code == 200
    songs = response.json()
    assert isinstance(songs, list)
    assert len(songs) >= 1
    
    # Check for the song we just added
    song = next((s for s in songs if s["name"] == "test_song_2"), None)
    assert song is not None
    assert song["instrument"] == "guitar"
    assert "vocals" in song["assets"]
    assert "backing" in song["assets"]
    assert "pitch" in song["assets"]

def test_process_with_unsupported_instrument():
    # Even if the backend supports guitar/piano, we should verify it handles parameters correctly
    file_content = b"fake audio data"
    file_name = "test_instrument.wav"
    files = {"file": (file_name, io.BytesIO(file_content), "audio/wav")}
    
    response = client.post("/process?instrument=piano", files=files)
    assert response.status_code == 200
    assert response.json()["instrument"] == "piano"
    assert "lyrics" not in response.json()["assets"] # No lyrics for piano

def test_progress_manager():
    pm = ProgressManager()
    pm.update("Test Task", "Doing something", 50)
    status = pm.status
    assert status["task"] == "Test Task"
    assert status["details"] == "Doing something"
    assert status["percentage"] == 50
