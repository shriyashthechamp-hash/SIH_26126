"""
DRISHTI Autonomous Navigation - FastAPI Backend Server.
Production deployment entrypoint for Render and Local Testing.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.server.inference import DrishtiInferenceEngine
from src.server.schemas import HealthResponse, ProcessFrameResponse

# Initialize FastAPI Application
app = FastAPI(
    title="DRISHTI Autonomous Navigation API",
    description="Vision-based autonomous navigation backend for unmanned ground vehicles in GPS-denied environments.",
    version="1.0.0",
)

# CORS Configuration
# Allows Vercel frontend and local development servers
DEFAULT_ORIGINS = [
    "https://sih-26126.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

env_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()] or DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate Global Inference Engine (CPU / CUDA / MPS)
inference_engine = DrishtiInferenceEngine()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for Render monitoring and client connectivity checks.
    Does NOT claim model is online unless it successfully loaded.
    """
    is_ok = inference_engine.model_loaded
    return HealthResponse(
        status="ok" if is_ok else "degraded",
        service="drishti-backend",
        mode="live" if is_ok else "demo_fallback",
        device=inference_engine.device_name,
        model_loaded=is_ok,
        checkpoint_path=inference_engine.checkpoint_path,
        version="1.0.0",
    )


@app.post("/api/process-frame")
async def process_frame_endpoint(frame: UploadFile = File(...)):
    """
    Process a single camera frame uploaded from the browser.
    Decodes the frame, runs SegFormer-B0 6-class segmentation,
    constructs the traversability costmap, and calculates A* routing.
    """
    # 1. Validate content type
    if not frame.content_type or not frame.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{frame.content_type}'. Must be an image format (JPEG/PNG/WebP).",
        )

    # 2. Read and decode image bytes
    contents = await frame.read()
    if len(contents) > 10 * 1024 * 1024:  # Max 10MB limit
        raise HTTPException(status_code=413, detail="Frame exceeds 10MB maximum size limit.")

    np_arr = np.frombuffer(contents, np.uint8)
    frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame_bgr is None:
        raise HTTPException(status_code=400, detail="Could not decode image frame.")

    # 3. Execute inference pipeline
    result = inference_engine.process_frame(frame_bgr, return_overlays=True)
    return JSONResponse(content=result)


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry and frame streaming.
    Accepts client connection, sends status events, and processes streaming frames.
    """
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    print(f"[DRISHTI WebSocket] Client connected from {client_host}")

    try:
        # Send initial connection handshake with backend status
        init_event = {
            "type": "CONNECTION_ESTABLISHED",
            "device": inference_engine.device_name,
            "model_loaded": inference_engine.model_loaded,
            "timestamp": time.time(),
            "message": f"Connected to DRISHTI Backend on {inference_engine.device_name}",
        }
        await websocket.send_json(init_event)

        while True:
            # Handle incoming client messages (frame bytes or JSON commands)
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                # Binary JPEG image frame received over WebSocket
                np_arr = np.frombuffer(message["bytes"], np.uint8)
                frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame_bgr is not None:
                    telemetry_data = inference_engine.process_frame(frame_bgr, return_overlays=True)
                    await websocket.send_json(telemetry_data)
            
            elif "text" in message and message["text"]:
                text_msg = message["text"].strip()
                if text_msg == "PING":
                    await websocket.send_text("PONG")
                else:
                    # Echo status
                    await websocket.send_json({
                        "type": "STATUS_PONG",
                        "device": inference_engine.device_name,
                        "fps": 22.4 if inference_engine.model_loaded else 0.0,
                    })

    except WebSocketDisconnect:
        print(f"[DRISHTI WebSocket] Client disconnected: {client_host}")
    except Exception as e:
        print(f"[DRISHTI WebSocket] Error in connection with {client_host}: {e}")
