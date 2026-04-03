#!/usr/bin/env python3
"""
Diamond Modeller — run the application.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting Diamond Modeller...")
    print("Open your browser and go to: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

