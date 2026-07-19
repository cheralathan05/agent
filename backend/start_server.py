"""Start the backend server with proper environment setup."""
import os
import sys

# Set environment before any imports
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5-coder")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

# Ensure PYTHONPATH includes project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
