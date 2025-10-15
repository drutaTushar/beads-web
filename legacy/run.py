#!/usr/bin/env python3
"""
Startup script for beads-web application.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.beads_web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )