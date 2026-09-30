#!/usr/bin/env python3
"""
Live Camera Navigation View for SIH 26126 Autonomous Rover.

Demonstrates end-to-end integration:
  REAL CAMERA
  → SEGFORMER PERCEPTION
  → TRAVERSABILITY MAPPING
  → COSTMAP ADAPTER
  → A* PATH PLANNER
  → PATH VALIDATOR
  → LIVE 4-PANEL DASHBOARD

DISCLAIMER:
  This script demonstrates live perception-to-planning orchestration.
  Coordinates are demo planning grid waypoints and are NOT physically metric-calibrated.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.perception.camera import create_camera_from_config
from src.traversability.costmap import TraversabilityCostmap, TraversabilityResult
from src.traversability.bev import BEVProjector
from src.planning.costmap_adapter import get_planning_arrays
from src.planning.astar import AStarPlanner
from src.planning.path_validator import validate_path, ValidationResult

# ===========================================================================
# CONSTANTS & CONFIGURATION
# ===========================================================================

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

# BGR colors matching the project standard
CLASS_COLORS = np.array([
    [0, 200, 0],       # 0: SMOOTH (Green)
    [0, 165, 255],     # 1: ROUGH (Orange)
    [0, 0, 255],       # 2: BUMPY (Red)
    [255, 0, 255],     # 3: FORBIDDEN (Magenta)
    [0, 0, 0],         # 4: OBSTACLE (Black)
    [180, 180, 180],   # 5: BACKGROUND (Gray)
], dtype=np.uint8)

# Dashboard sizing
DASHBOARD_WIDTH = 1280
DASHBOARD_HEIGHT = 820
PANEL_WIDTH = 610
PANEL_HEIGHT = 320

PLANNING_GRID_SIZE = 80  # 80x80 BEV grid for responsive real-time A*


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

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
    out_w: int = PANEL_WIDTH,
    out_h: int = PANEL_HEIGHT,
) -> np.ndarray:
    """
    Render Panel 4: High-contrast A* navigation map in BEV grid space.
    Shows traversable terrain, blocked areas, START, GOAL, and A* path.
    """
    grid_rows, grid_cols = plan_costmap.shape

    # 1. Base cost visualization (TURBO or custom cost colormap)
    cost_uint8 = np.clip(plan_costmap * 255.0, 0, 255).astype(np.uint8)
    base_color = cv2.applyColorMap(cost_uint8, cv2.COLORMAP_TURBO)

    # Highlight blocked cells distinctly with dark charcoal/red
    base_color[plan_blocked] = [30, 30, 200]

    # Resize to panel dimensions
    nav_map = cv2.resize(base_color, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    # Scale factor from grid coordinates to panel pixels
    scale_x = out_w / float(grid_cols)
    scale_y = out_h / float(grid_rows)

    # Subtle grid lines
    grid_spacing = 10
    for r in range(grid_spacing, grid_rows, grid_spacing):
        y_px = int(round(r * scale_y))
        cv2.line(nav_map, (0, y_px), (out_w, y_px), (60, 60, 60), 1, cv2.LINE_AA)
    for c in range(grid_spacing, grid_cols, grid_spacing):
        x_px = int(round(c * scale_x))
        cv2.line(nav_map, (x_px, 0), (x_px, out_h), (60, 60, 60), 1, cv2.LINE_AA)

    # 2. Draw A* planned path
    if path and len(path) > 1:
        path_color = (255, 255, 0) if path_valid else (0, 165, 255)  # Cyan if valid, orange if invalid
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            pt1 = (int(round(c1 * scale_x)), int(round(r1 * scale_y)))
            pt2 = (int(round(c2 * scale_x)), int(round(r2 * scale_y)))
            cv2.line(nav_map, pt1, pt2, path_color, 3, cv2.LINE_AA)
            cv2.circle(nav_map, pt1, 2, (255, 255, 255), -1)
    elif not path:
        # Warning banner if no path could be found
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

    # 3. Draw START marker (Green circle with 'S' and high-contrast label)
    start_x = int(round(start[1] * scale_x))
    start_y = int(round(start[0] * scale_y))
    cv2.circle(nav_map, (start_x, start_y), 9, (0, 255, 0), -1, cv2.LINE_AA)
    cv2.circle(nav_map, (start_x, start_y), 9, (0, 0, 0), 2, cv2.LINE_AA)
    # Outline + text for readability
    cv2.putText(nav_map, "START", (start_x + 12, start_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "START", (start_x + 12, start_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    # 4. Draw GOAL marker (Red star/circle with 'G' and high-contrast label)
    goal_x = int(round(goal[1] * scale_x))
    goal_y = int(round(goal[0] * scale_y))
    cv2.circle(nav_map, (goal_x, goal_y), 9, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(nav_map, (goal_x, goal_y), 9, (255, 255, 255), 2, cv2.LINE_AA)
    # Outline + text for readability
    cv2.putText(nav_map, "GOAL", (goal_x + 12, goal_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(nav_map, "GOAL", (goal_x + 12, goal_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # Demo coordinate disclaimer watermark
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


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Live Camera Navigation View for SIH 26126.")
    parser.add_argument("--camera-config", default="configs/camera.yaml", help="Path to camera YAML config.")
    parser.add_argument("--bev-config", default="configs/bev.yaml", help="Path to BEV YAML config.")
    parser.add_argument("--trav-config", default="configs/traversability.yaml", help="Path to traversability YAML config.")
    parser.add_argument("--max-frames", type=int, default=None, help="Process at most N frames and exit cleanly.")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display (saves frame to disk).")
    args = parser.parse_args()

    # Determine execution device
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        device_name = "MPS (Apple Silicon)"
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        device_name = "CUDA GPU"
    else:
        device = torch.device("cpu")
        device_name = "CPU"

    # Startup Banner (Prompt requirement)
    print("=" * 60)
    print("LIVE NAVIGATION PIPELINE")
    print(f"Camera: {args.camera_config}")
    print(f"Model:  {MODEL_NAME}")
    print(f"Device: {device_name}")
    print("=" * 60)

    # 1. Load SegFormer Model
    print("Loading perception model...")
    processor = SegformerImageProcessor.from_pretrained(MODEL_NAME)
    model = SegformerForSemanticSegmentation.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_CLASSES,
        ignore_mismatched_sizes=True,
    )
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    print("Model loaded successfully.")

    # 2. Initialize Traversability & BEV Projector
    costmap_generator = TraversabilityCostmap(args.trav_config)
    bev_projector = BEVProjector(args.bev_config)
    print("Traversability costmap & BEV projector initialized.")

    # 3. Open Camera
    print("Opening camera source...")
    try:
        cap = create_camera_from_config(args.camera_config)
    except Exception as e:
        print(f"Camera Initialization Error: {e}")
        sys.exit(1)

    if not cap.is_opened():
        print(f"Could not open camera from {args.camera_config}. Check connection/permissions.")
        sys.exit(1)

    # Confirmation Banner (Prompt requirement)
    print("Live navigation pipeline: RUNNING")
    print("Press 'q' or 'ESC' in the dashboard window to exit.")

    # Loop variables
    frame_count = 0
    fps_smooth = 0.0
    last_loop_time = time.perf_counter()

    # Pre-allocate dashboard canvas
    dashboard = np.zeros((DASHBOARD_HEIGHT, DASHBOARD_WIDTH, 3), dtype=np.uint8)

    # Demo Planning Coordinates in BEV Grid Space:
    # Rover starts near bottom center, aims forward towards top center
    demo_start_nominal = (PLANNING_GRID_SIZE - 12, PLANNING_GRID_SIZE // 2)
    demo_goal_nominal = (12, PLANNING_GRID_SIZE // 2)

    with torch.no_grad():
        while True:
            loop_start = time.perf_counter()

            # -------------------------------------------------------------
            # STEP 1: Capture Frame
            # -------------------------------------------------------------
            ret, frame = cap.read()
            if not ret or frame is None:
                print("End of camera stream or failed to grab frame.")
                break

            frame_count += 1
            h, w = frame.shape[:2]

            # -------------------------------------------------------------
            # STEP 2: SegFormer Inference
            # -------------------------------------------------------------
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(rgb)

            inputs = processor(images=image_pil, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(device)

            outputs = model(pixel_values=pixel_values)
            logits = outputs.logits
            logits = torch.nn.functional.interpolate(
                logits, size=(h, w), mode="bilinear", align_corners=False
            )
            prediction = torch.argmax(logits, dim=1)[0]
            mask = prediction.detach().cpu().numpy().astype(np.uint8)

            # Segmentation overlay
            seg_color = CLASS_COLORS[mask]
            overlay = cv2.addWeighted(frame, 0.5, seg_color, 0.5, 0)

            # -------------------------------------------------------------
            # STEP 3: Traversability Costmap
            # -------------------------------------------------------------
            trav_result: TraversabilityResult = costmap_generator.process(mask)

            # -------------------------------------------------------------
            # STEP 4: BEV Projection & Costmap Adapter for Planning
            # -------------------------------------------------------------
            # Project segmentation mask to BEV space
            bev_mask = bev_projector.project(mask, is_mask=True)
            # Downsample BEV to planning grid
            bev_grid = cv2.resize(
                bev_mask, (PLANNING_GRID_SIZE, PLANNING_GRID_SIZE), interpolation=cv2.INTER_NEAREST
            )

            # Process BEV through TraversabilityCostmap to obtain costs & obstacles
            bev_trav_res: TraversabilityResult = costmap_generator.process(bev_grid)
            plan_costmap, plan_blocked = get_planning_arrays(bev_trav_res)

            blocked_count = int(np.sum(plan_blocked))
            total_cells = plan_blocked.size
            blocked_pct = (blocked_count / total_cells) * 100.0

            # -------------------------------------------------------------
            # STEP 5: Define Planning Start & Goal (Demo Grid Coordinates)
            # -------------------------------------------------------------
            start_cell = find_nearest_free_cell(demo_start_nominal, plan_blocked)
            goal_cell = find_nearest_free_cell(demo_goal_nominal, plan_blocked)

            # -------------------------------------------------------------
            # STEP 6: Run A* Planner
            # -------------------------------------------------------------
            planner = AStarPlanner(costmap=plan_costmap, blocked_mask=plan_blocked)
            planned_path = planner.plan(start=start_cell, goal=goal_cell)
            path_found = len(planned_path) > 0

            # -------------------------------------------------------------
            # STEP 7: Validate Path
            # -------------------------------------------------------------
            val_result: ValidationResult = validate_path(
                planned_path, blocked_mask=plan_blocked, costmap=plan_costmap
            )
            path_valid = val_result.valid if path_found else False

            # -------------------------------------------------------------
            # STEP 8: Render 4-Panel Dashboard
            # -------------------------------------------------------------
            dashboard.fill(18)  # Sleek dark background

            # Header Bar
            cv2.putText(
                dashboard,
                "SIH 26126 — LIVE AUTONOMOUS CAMERA NAVIGATION PIPELINE",
                (20, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                dashboard,
                f"Device: {device_name} | Res: {w}x{h}",
                (DASHBOARD_WIDTH - 340, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

            # Resize Panels
            p1_img = cv2.resize(frame, (PANEL_WIDTH, PANEL_HEIGHT))
            p2_img = cv2.resize(overlay, (PANEL_WIDTH, PANEL_HEIGHT))
            p3_img = cv2.resize(trav_result.visualization, (PANEL_WIDTH, PANEL_HEIGHT))
            p4_img = render_navigation_map(
                plan_costmap=plan_costmap,
                plan_blocked=plan_blocked,
                start=start_cell,
                goal=goal_cell,
                path=planned_path,
                path_valid=path_valid,
                out_w=PANEL_WIDTH,
                out_h=PANEL_HEIGHT,
            )

            # Panel Layout Coordinates:
            # Row 1: y = 55 to 375
            # Row 2: y = 405 to 725
            r1_y = 55
            r2_y = 405
            c1_x = 20
            c2_x = 650

            dashboard[r1_y : r1_y + PANEL_HEIGHT, c1_x : c1_x + PANEL_WIDTH] = p1_img
            dashboard[r1_y : r1_y + PANEL_HEIGHT, c2_x : c2_x + PANEL_WIDTH] = p2_img
            dashboard[r2_y : r2_y + PANEL_HEIGHT, c1_x : c1_x + PANEL_WIDTH] = p3_img
            dashboard[r2_y : r2_y + PANEL_HEIGHT, c2_x : c2_x + PANEL_WIDTH] = p4_img

            # Panel Titles
            cv2.putText(
                dashboard, "PANEL 1: RAW CAMERA FRAME", (c1_x, r1_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 200), 1, cv2.LINE_AA
            )
            cv2.putText(
                dashboard, "PANEL 2: SEGMENTATION OVERLAY", (c2_x, r1_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 200), 1, cv2.LINE_AA
            )
            cv2.putText(
                dashboard, "PANEL 3: TRAVERSABILITY COSTMAP", (c1_x, r2_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 200), 1, cv2.LINE_AA
            )
            cv2.putText(
                dashboard, "PANEL 4: A* NAVIGATION MAP (BEV/GRID)", (c2_x, r2_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 200), 1, cv2.LINE_AA
            )

            # Subtle borders around panels
            for px, py in [(c1_x, r1_y), (c2_x, r1_y), (c1_x, r2_y), (c2_x, r2_y)]:
                cv2.rectangle(
                    dashboard,
                    (px - 1, py - 1),
                    (px + PANEL_WIDTH + 1, py + PANEL_HEIGHT + 1),
                    (70, 70, 70),
                    1,
                )

            # -------------------------------------------------------------
            # Status Area (Prompt Requirements)
            # -------------------------------------------------------------
            status_y = 750
            cv2.rectangle(
                dashboard,
                (20, status_y - 12),
                (DASHBOARD_WIDTH - 20, DASHBOARD_HEIGHT - 15),
                (30, 30, 30),
                -1,
            )
            cv2.rectangle(
                dashboard,
                (20, status_y - 12),
                (DASHBOARD_WIDTH - 20, DASHBOARD_HEIGHT - 15),
                (75, 75, 75),
                1,
            )

            # Status line 1: Core System Flags
            path_status_str = "FOUND" if path_found else "NO PATH"
            path_status_color = (0, 255, 0) if path_found else (0, 0, 255)
            val_status_str = "YES" if path_valid else "NO"
            val_status_color = (0, 255, 0) if path_valid else (0, 0, 255)

            col_w = 200
            # Col 1: SEGMENTATION: OK
            cv2.putText(dashboard, "SEGMENTATION: ", (35, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
            cv2.putText(dashboard, "OK", (165, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)

            # Col 2: COSTMAP: OK
            cv2.putText(dashboard, "COSTMAP: ", (35 + col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
            cv2.putText(dashboard, "OK", (115 + col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)

            # Col 3: PATH: FOUND / NO PATH
            cv2.putText(dashboard, "PATH: ", (35 + 2 * col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
            cv2.putText(dashboard, path_status_str, (90 + 2 * col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, path_status_color, 2)

            # Col 4: PATH VALID: YES / NO
            cv2.putText(dashboard, "PATH VALID: ", (35 + 3 * col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
            cv2.putText(dashboard, val_status_str, (135 + 3 * col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, val_status_color, 2)

            # Col 5: BLOCKED CELLS: N
            cv2.putText(dashboard, f"BLOCKED CELLS: {blocked_count} ({blocked_pct:.1f}%)", (35 + 4 * col_w, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)

            # Col 6: FPS: N
            cv2.putText(dashboard, f"FPS: {fps_smooth:.1f}", (DASHBOARD_WIDTH - 125, status_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 2)

            # Status line 2: Contextual Demo Planning Details
            plan_info = (
                f"DEMO PLANNING COORDINATES: Start ({start_cell[0]}, {start_cell[1]}) -> "
                f"Goal ({goal_cell[0]}, {goal_cell[1]}) | Path Length: {len(planned_path)} waypoints | "
                "[NOT METRIC-CALIBRATED] | Exit: 'q' or ESC"
            )
            cv2.putText(
                dashboard,
                plan_info,
                (35, status_y + 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (170, 170, 170),
                1,
                cv2.LINE_AA,
            )

            # FPS calculation
            elapsed = time.perf_counter() - loop_start
            instant_fps = 1.0 / max(elapsed, 1e-6)
            fps_smooth = 0.85 * fps_smooth + 0.15 * instant_fps if fps_smooth > 0 else instant_fps

            # -------------------------------------------------------------
            # STEP 9: Display or Save
            # -------------------------------------------------------------
            if args.headless:
                out_path = Path("outputs") / "live_navigation_demo.png"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_path), dashboard)
                print(f"[Frame {frame_count}] Processed frame. Saved demo screenshot to {out_path}.")
            else:
                cv2.imshow("SIH 26126 — Live Camera Navigation View", dashboard)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    print("Exit requested by user.")
                    break

            if args.max_frames and frame_count >= args.max_frames:
                print(f"Reached target frame count ({args.max_frames}). Exiting cleanly.")
                break

    # Cleanup
    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()
    print("Live camera navigation pipeline stopped cleanly.")


if __name__ == "__main__":
    main()
