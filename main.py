#!/usr/bin/env python3
import sys
import subprocess

# Manual check for required packages
required = ["fastapi", "uvicorn", "httpx", "openai", "pypdf", "python-multipart", "gunicorn"]
for pkg in required:
    try:
        __import__(pkg)
        print(f"{pkg} installed")
    except ImportError:
        print(f"{pkg} NOT installed - trying to install")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from app import app
import uvicorn
import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting StudyBuddy on http://0.0.0.0:{port}")
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')