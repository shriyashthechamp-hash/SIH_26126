"""
FastAPI + WebSocket Application for Live Autonomous Navigation Dashboard.

Streams synchronized 4-panel navigation data from the iPhone/OpenCV camera
to the browser at http://localhost:8000.
"""

import asyncio
import base64
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.perception.camera import create_camera_from_config
from src.traversability.costmap import TraversabilityCostmap, TraversabilityResult
from src.traversability.bev import BEVProjector
from src.planning.costmap_adapter import get_planning_arrays
from src.planning.astar import AStarPlanner
from src.planning.path_validator import validate_path, ValidationResult

# Constants
MODEL_NAME = "nvidia/segformer-b0-finetuned-ade-512-512"
CHECKPOINT_PATH = "experiments/rellis_segformer_b0_baseline/best_model.pt"

NUM_CLASSES = 6
CLASS_NAMES = [
    "SMOOTH",
    "ROUGH",
    "BUMPY",
    "FORBIDDEN",
    "OBSTACLE",
    "BACKGROUND",
]

CLASS_COLORS = np.array([
    [0, 200, 0],       # 0: SMOOTH (Green)
    [0, 165, 255],     # 1: ROUGH (Orange)
    [0, 0, 255],       # 2: BUMPY (Red)
    [255, 0, 255],     # 3: FORBIDDEN (Magenta)
    [0, 0, 0],         # 4: OBSTACLE (Black)
    [180, 180, 180],   # 5: BACKGROUND (Gray)
], dtype=np.uint8)

PLANNING_GRID_SIZE = 80
STATIC_DIR = Path(__file__).resolve().parent / "static"


def find_nearest_free_cell(
    point: Tuple[int, int],
    blocked_mask: np.ndarray,
    search_radius: int = 12,
) -> Tuple[int, int]:
    """Find the closest unblocked cell if target point falls on an obstacle."""
    r, c = point
    rows, cols = blocked_mask.shape
    if 0 <= r < rows and 0 <= c < cols and not blocked_mask[r, c]:
        return (r, c)

    for rad in range(1, search_radius + 1):
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not blocked_mask[nr, nc]:
                        return (nr, nc)
    return point


def render_navigation_map(
    plan_costmap: np.ndarray,
    plan_blocked: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    path: List[Tuple[int, int]],
    path_valid: bool,
    out_w: int = 600,
    out_h: int = 340,
) -> np.ndarray:
    """Render Panel 4: High-contrast A* navigation map in BEV grid space."""
    grid_rows, grid_cols = plan_costmap.shape

    cost_uint8 = np.clip(plan_costmap * 255.0, 0, 255).astype(np.uint8)
    base_color = cv2.applyColorMap(cost_uint8, cv2.COLORMAP_TURBO)
    base_color[plan_blocked] = [30, 30, 200]

    nav_map = cv2.resize(base_color, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    scale_x = out_w / float(grid_cols)
    scale_y = out_h / float(grid_rows)

    # Grid lines
    grid_spacing = 10
    for r in range(grid_spacing, grid_rows, grid_spacing):
        y_px = int(round(r * scale_y))
        cv2.line(nav_map, (0, y_px), (out_w, y_px), (60, 60, 60), 1, cv2.LINE_AA)
    for c in range(grid_spacing, grid_cols, grid_spacing):
        x_px = int(round(c * scale_x))
        cv2.line(nav_map, (x_px, 0), (x_px, out_h), (60, 60, 60), 1, cv2.LINE_AA)

    # Path
    if path and len(path) > 1:
        path_color = (255, 255, 0) if path_valid else (0, 165, 255)
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            pt1 = (int(round(c1 * scale_x)), int(round(r1 * scale_y)))
            pt2 = (int(round(c2 * scale_x)), int(round(r2 * scale_y)))
            cv2.line(nav_map, pt1, pt2, path_color, 3, cv2.LINE_AA)
            cv2.circle(nav_map, pt1, 2, (255, 255, 255), -1)
    elif not path:
        cv2.putText(
            nav_map,
            "NO VALID ROUTE FOUND",
            (out_w // 2 - 130, out_h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    # START
    start_x = int(round(start[1] * scale_x))
    start_y = int(round(start[0] * scale_y))
    cv2.circle(nav_map, (start_x, start_y), 9, (0, 255, 0), -1, cv2.LINE_AA)
    cv2.circle(nav_map, (start_x, start_y), 9, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "START", (start_x + 12, start_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "START", (start_x + 12, start_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # GOAL
    goal_x = int(round(goal[1] * scale_x))
    goal_y = int(round(goal[0] * scale_y))
    cv2.circle(nav_map, (goal_x, goal_y), 9, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(nav_map, (goal_x, goal_y), 9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "GOAL", (goal_x + 12, goal_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "GOAL", (goal_x + 12, goal_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # Watermark
    cv2.putText(
        nav_map,
        "[DEMO PLANNING GRID — NOT METRIC]",
        (10, out_h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    return nav_map


def encode_jpeg_base64(img: np.ndarray, quality: int = 80) -> str:
    """Encode OpenCV BGR image as Base64 JPEG string."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", img, encode_param)
    if not success:
        return ""
    return base64.b64encode(buffer).decode("utf-8")


class NavigationPipelineRunner:
    """Manages continuous background processing of camera frames."""

    def __init__(
        self,
        camera_config: str = "configs/camera.yaml",
        bev_config: str = "configs/bev.yaml",
        trav_config: str = "configs/traversability.yaml",
    ):
        self.camera_config = camera_config
        self.bev_config = bev_config
        self.trav_config = trav_config

        # Device detection
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            self.device_name = "MPS (Apple Silicon)"
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            self.device_name = "CUDA GPU"
        else:
            self.device = torch.device("cpu")
            self.device_name = "CPU"

        # Model & components
        self.processor = SegformerImageProcessor.from_pretrained(MODEL_NAME)
        self.model = SegformerForSemanticSegmentation.from_pretrained(
            MODEL_NAME,
            num_labels=NUM_CLASSES,
            ignore_mismatched_sizes=True,
        )
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.costmap_generator = TraversabilityCostmap(self.trav_config)
        self.bev_projector = BEVProjector(self.bev_config)

        self.cap = create_camera_from_config(self.camera_config)
        self.running = False
        self.latest_payload: Optional[Dict] = None
        self.active_websockets: Set[WebSocket] = set()

        self.demo_start = (PLANNING_GRID_SIZE - 12, PLANNING_GRID_SIZE // 2)
        self.demo_goal = (12, PLANNING_GRID_SIZE // 2)

    def start_loop(self):
        """Start async frame processing loop."""
        self.running = True
        asyncio.create_task(self._process_frames())

    def stop(self):
        """Stop frame processing."""
        self.running = False
        if self.cap and self.cap.is_opened():
            self.cap.release()

    async def _process_frames(self):
        """Continuous pipeline loop."""
        fps_smooth = 0.0

        with torch.no_grad():
            while self.running:
                t0 = time.perf_counter()

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    await asyncio.sleep(0.05)
                    continue

                h, w = frame.shape[:2]

                # 1. SegFormer Inference
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image_pil = Image.fromarray(rgb)
                inputs = self.processor(images=image_pil, return_tensors="pt")
                pixel_values = inputs["pixel_values"].to(self.device)

                outputs = self.model(pixel_values=pixel_values)
                logits = torch.nn.functional.interpolate(
                    outputs.logits, size=(h, w), mode="bilinear", align_corners=False
                )
                prediction = torch.argmax(logits, dim=1)[0]
                mask = prediction.detach().cpu().numpy().astype(np.uint8)

                # 2. Overlays
                seg_color = CLASS_COLORS[mask]
                overlay = cv2.addWeighted(frame, 0.5, seg_color, 0.5, 0)

                # 3. Traversability
                trav_result: TraversabilityResult = self.costmap_generator.process(mask)

                # 4. BEV Projection & Costmap Adapter
                bev_mask = self.bev_projector.project(mask, is_mask=True)
                bev_grid = cv2.resize(
                    bev_mask, (PLANNING_GRID_SIZE, PLANNING_GRID_SIZE), interpolation=cv2.INTER_NEAREST
                )
                bev_trav_res = self.costmap_generator.process(bev_grid)
                plan_costmap, plan_blocked = get_planning_arrays(bev_trav_res)

                blocked_count = int(np.sum(plan_blocked))
                total_cells = plan_blocked.size
                blocked_pct = (blocked_count / total_cells) * 100.0

                # 5. Planning
                start_cell = find_nearest_free_cell(self.demo_start, plan_blocked)
                goal_cell = find_nearest_free_cell(self.demo_goal, plan_blocked)

                planner = AStarPlanner(costmap=plan_costmap, blocked_mask=plan_blocked)
                planned_path = planner.plan(start=start_cell, goal=goal_cell)
                path_found = len(planned_path) > 0

                val_result: ValidationResult = validate_path(
                    planned_path, blocked_mask=plan_blocked, costmap=plan_costmap
                )
                path_valid = val_result.valid if path_found else False

                # 6. Render Panel 4 (Navigation Map)
                nav_map = render_navigation_map(
                    plan_costmap=plan_costmap,
                    plan_blocked=plan_blocked,
                    start=start_cell,
                    goal=goal_cell,
                    path=planned_path,
                    path_valid=path_valid,
                    out_w=600,
                    out_h=340,
                )

                # Resize image panels for efficient web streaming
                panel_raw = cv2.resize(frame, (600, 340))
                panel_seg = cv2.resize(overlay, (600, 340))
                panel_trav = cv2.resize(trav_result.visualization, (600, 340))

                # Encode images to JPEG Base64
                b64_raw = encode_jpeg_base64(panel_raw, quality=75)
                b64_seg = encode_jpeg_base64(panel_seg, quality=75)
                b64_trav = encode_jpeg_base64(panel_trav, quality=75)
                b64_nav = encode_jpeg_base64(nav_map, quality=80)

                dt = time.perf_counter() - t0
                instant_fps = 1.0 / max(dt, 1e-6)
                fps_smooth = 0.85 * fps_smooth + 0.15 * instant_fps if fps_smooth > 0 else instant_fps

                self.latest_payload = {
                    "raw": b64_raw,
                    "segmentation": b64_seg,
                    "traversability": b64_trav,
                    "navigation": b64_nav,
                    "seg_status": "OK",
                    "costmap_status": "OK",
                    "path_found": path_found,
                    "path_valid": path_valid,
                    "path_len": len(planned_path),
                    "blocked_cells": blocked_count,
                    "blocked_pct": blocked_pct,
                    "fps": fps_smooth,
                    "device": self.device_name,
                    "start": [start_cell[0], start_cell[1]],
                    "goal": [goal_cell[0], goal_cell[1]],
                }

                # Broadcast to connected WebSockets
                if self.active_websockets:
                    dead_sockets = set()
                    for ws in list(self.active_websockets):
                        try:
                            await ws.send_json(self.latest_payload)
                        except Exception:
                            dead_sockets.add(ws)
                    self.active_websockets -= dead_sockets

                await asyncio.sleep(0.01)


def create_app(
    camera_config: str = "configs/camera.yaml",
    bev_config: str = "configs/bev.yaml",
    trav_config: str = "configs/traversability.yaml",
) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(title="SIH 26126 Navigation Server")
    runner = NavigationPipelineRunner(
        camera_config=camera_config,
        bev_config=bev_config,
        trav_config=trav_config,
    )
    app.state.runner = runner

    @app.on_event("startup")
    async def on_startup():
        runner.start_loop()

    @app.on_event("shutdown")
    async def on_shutdown():
        runner.stop()

    @app.get("/")
    async def serve_dashboard():
        index_file = STATIC_DIR / "index.html"
        return FileResponse(index_file)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        runner.active_websockets.add(websocket)
        try:
            # Send latest frame immediately if ready
            if runner.latest_payload:
                await websocket.send_json(runner.latest_payload)
            while True:
                # Keep socket alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            runner.active_websockets.discard(websocket)
        except Exception:
            runner.active_websockets.discard(websocket)

    return app
