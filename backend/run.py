"""Direct server launcher - avoids module caching issues."""
import os, sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set env vars BEFORE any imports
os.environ["OLLAMA_MODEL"] = "qwen2.5-coder"

# Import the app directly in this process
from backend.app.main import app

# Start uvicorn with the app object (not string)
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")
