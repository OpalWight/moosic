import PyInstaller.__main__
import os
import shutil

def build():
    # Define the entry point for the FastAPI server
    entry_point = "main.py"
    
    # Define PyInstaller options
    opts = [
        entry_point,
        "--onefile",
        "--name=moosic-backend",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi",
        "--collect-all=demucs",
        "--collect-all=whisper",
        "--collect-all=librosa",
    ]
    
    print(f"Building moosic-backend with options: {opts}")
    PyInstaller.__main__.run(opts)
    
    # Cleanup (optional)
    # shutil.rmtree("build")
    # os.remove("moosic-backend.spec")

if __name__ == "__main__":
    build()
