#!/usr/bin/env python3
"""
Localhost Web Dashboard Launcher for Live Autonomous Camera Navigation.

Launches the FastAPI server at http://localhost:8000 and streams synchronized
4-panel perception and A* navigation data to the browser over WebSocket.
"""

import argparse
import os
import sys
from pathlib import Path
import uvicorn
import torch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.server.app import create_app


def main():
    parser = argparse.ArgumentParser(description="Run Live Navigation Dashboard on Localhost.")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--camera-config", default="configs/camera.yaml", help="Path to camera config")
    parser.add_argument("--bev-config", default="configs/bev.yaml", help="Path to BEV config")
    parser.add_argument("--trav-config", default="configs/traversability.yaml", help="Path to traversability config")
    args = parser.parse_args()

    # Determine device name for banner
    if torch.backends.mps.is_available():
        device_name = "MPS"
    elif torch.cuda.is_available():
        device_name = "CUDA"
    else:
        device_name = "CPU"

    # Terminal Startup Banner
    print("=" * 60)
    print("LOCAL NAVIGATION DASHBOARD")
    print("Camera: iPhone Continuity Camera")
    print("Model:  SegFormer-B0")
    print(f"Device: {device_name}")
    print(f"Server: http://localhost:{args.port}")
    print("=" * 60)
    print("Live navigation dashboard: RUNNING")
    print(f"Open http://localhost:{args.port} in your browser to view the live dashboard.")
    print("Press Ctrl+C to stop.")
    print()

    # Create app instance
    app = create_app(
        camera_config=args.camera_config,
        bev_config=args.bev_config,
        trav_config=args.trav_config,
    )

    # Run uvicorn server
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
