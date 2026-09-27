import time
import cv2
import numpy as np
import torch
import sys
from pathlib import Path
from PIL import Image
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from dataclasses import dataclass

# Add src to path so we can import perception
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.perception.camera import create_camera_from_config
from src.traversability.costmap import TraversabilityCostmap

# ============================================================
# CONFIG
# ============================================================

MODEL_NAME = "nvidia/segformer-b0-finetuned-ade-512-512"
CHECKPOINT = "experiments/rellis_segformer_b0_baseline/best_model.pt"

NUM_CLASSES = 6

CLASS_NAMES = [
    "SMOOTH",
    "ROUGH",
    "BUMPY",
    "FORBIDDEN",
    "OBSTACLE",
    "BACKGROUND",
]

# BGR colors
CLASS_COLORS = np.array([
    [0, 200, 0],       # SMOOTH
    [0, 165, 255],     # ROUGH
    [0, 0, 255],       # BUMPY
    [255, 0, 255],     # FORBIDDEN
    [0, 0, 0],         # OBSTACLE
    [180, 180, 180],   # BACKGROUND
], dtype=np.uint8)

@dataclass
class SegmentationResult:
    frame: np.ndarray
    mask: np.ndarray
    overlay: np.ndarray
    class_distribution: dict
    inference_time: float
    timestamp: float

# ============================================================
# DEVICE
# ============================================================

if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
    DEVICE_NAME = "MPS"
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    DEVICE_NAME = "CUDA"
else:
    DEVICE = torch.device("cpu")
    DEVICE_NAME = "CPU"

print("=" * 60)
print("SIH 26126 — LIVE UGV DASHBOARD")
print("=" * 60)
print(f"Device: {DEVICE_NAME}")
print(f"Model:  {MODEL_NAME}")
print(f"Checkpoint: {CHECKPOINT}")
print("=" * 60)

# ============================================================
# LOAD MODEL & TRAVERSABILITY
# ============================================================

processor = SegformerImageProcessor.from_pretrained(MODEL_NAME)

model = SegformerForSemanticSegmentation.from_pretrained(
    MODEL_NAME,
    num_labels=NUM_CLASSES,
    ignore_mismatched_sizes=True,
)

checkpoint = torch.load(CHECKPOINT, map_location="cpu")
model.load_state_dict(checkpoint["model_state_dict"])
model.to(DEVICE)
model.eval()

print("Model loaded successfully.")

costmap_generator = TraversabilityCostmap("configs/traversability.yaml")
print("Traversability costmap initialized.")

print("Opening camera...")

# ============================================================
# CAMERA
# ============================================================

try:
    cap = create_camera_from_config("configs/camera.yaml")
except Exception as e:
    print(f"Camera Initialization Error: {e}")
    sys.exit(1)

if not cap.is_opened():
    print("Could not open camera. Check URL or permissions.")
    sys.exit(1)

# ============================================================
# INFERENCE & DASHBOARD LOOP
# ============================================================

previous_time = time.perf_counter()
end_to_end_fps = 0.0
capture_fps = 0.0
last_capture_time = time.perf_counter()

DASHBOARD_WIDTH = 1280
DASHBOARD_HEIGHT = 800

with torch.no_grad():
    while True:
        loop_start_time = time.perf_counter()

        ret, frame = cap.read()
        
        capture_time = time.perf_counter()
        inst_cap_fps = 1.0 / max(capture_time - last_capture_time, 1e-6)
        capture_fps = 0.9 * capture_fps + 0.1 * inst_cap_fps
        last_capture_time = capture_time

        if not ret or frame is None:
            print("Failed to read camera frame. Stream might have ended or disconnected.")
            break

        start_inference_time = time.perf_counter()

        # OpenCV BGR -> RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        inputs = processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(DEVICE)

        outputs = model(pixel_values=pixel_values)
        logits = outputs.logits

        # Resize logits to original frame size
        h, w = frame.shape[:2]
        logits = torch.nn.functional.interpolate(
            logits,
            size=(h, w),
            mode="bilinear",
            align_corners=False,
        )

        prediction = torch.argmax(logits, dim=1)[0]
        mask = prediction.detach().cpu().numpy().astype(np.uint8)

        inference_time_s = time.perf_counter() - start_inference_time

        # ----------------------------------------------------
        # Segmentation Result
        # ----------------------------------------------------
        segmentation = CLASS_COLORS[mask]
        overlay = cv2.addWeighted(frame, 0.5, segmentation, 0.5, 0)
        
        counts = np.bincount(mask.flatten(), minlength=NUM_CLASSES)
        total_pixels = max(counts.sum(), 1)
        distribution = {CLASS_NAMES[i]: (counts[i] / total_pixels) * 100 for i in range(NUM_CLASSES)}

        result = SegmentationResult(
            frame=frame.copy(),
            mask=mask.copy(),
            overlay=overlay.copy(),
            class_distribution=distribution,
            inference_time=inference_time_s,
            timestamp=time.time()
        )

        # ----------------------------------------------------
        # Traversability Result
        # ----------------------------------------------------
        trav_result = costmap_generator.process(result.mask)

        # ----------------------------------------------------
        # BUILD DASHBOARD
        # ----------------------------------------------------
        dashboard = np.zeros((DASHBOARD_HEIGHT, DASHBOARD_WIDTH, 3), dtype=np.uint8)
        
        # We will put 3 images side by side: Original, Overlay, Costmap
        panel_w, panel_h = 410, 300
        
        resized_frame = cv2.resize(frame, (panel_w, panel_h))
        resized_overlay = cv2.resize(result.overlay, (panel_w, panel_h))
        resized_costmap = cv2.resize(trav_result.visualization, (panel_w, panel_h))
        
        # Place images
        dashboard[20:20+panel_h, 10:10+panel_w] = resized_frame
        dashboard[20:20+panel_h, 435:435+panel_w] = resized_overlay
        dashboard[20:20+panel_h, 860:860+panel_w] = resized_costmap
        
        cv2.putText(dashboard, "MAIN CAMERA", (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(dashboard, "SEGMENTATION OVERLAY", (435, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(dashboard, "TRAVERSABILITY COSTMAP", (860, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Bottom section panels
        base_y = panel_h + 50
        
        # Legend (under segmentation)
        cv2.putText(dashboard, "SEGMENTATION LEGEND", (435, base_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for i, name in enumerate(CLASS_NAMES):
            color = tuple(int(c) for c in CLASS_COLORS[i])
            row = i % 3
            col = i // 3
            x_pos = 435 + col * 150
            y_pos = base_y + 30 + row * 30
            cv2.rectangle(dashboard, (x_pos, y_pos - 15), (x_pos + 15, y_pos), color, -1)
            cv2.putText(dashboard, name, (x_pos + 25, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # System Status
        cv2.putText(dashboard, "SYSTEM STATUS", (10, base_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(dashboard, f"Camera: CONNECTED", (10, base_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(dashboard, f"Model: {MODEL_NAME.split('/')[-1]}", (10, base_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(dashboard, f"Device: {DEVICE_NAME}", (10, base_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(dashboard, f"Capture FPS: {capture_fps:.1f}", (10, base_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(dashboard, f"Inference: {inference_time_s * 1000:.1f} ms", (10, base_y + 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(dashboard, f"End-to-End FPS: {end_to_end_fps:.1f}", (10, base_y + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Traversability Metrics
        dist_x = 860
        cv2.putText(dashboard, "TRAVERSABILITY METRICS", (dist_x, base_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(dashboard, f"Mean Cost: {trav_result.mean_cost:.3f}", (dist_x, base_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(dashboard, f"Traversable: {trav_result.percent_traversable:.1f}%", (dist_x, base_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        cv2.putText(dashboard, f"Unknown: {trav_result.percent_unknown:.1f}%", (dist_x, base_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1)
        cv2.putText(dashboard, f"Blocked: {trav_result.percent_blocked:.1f}%", (dist_x, base_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 200), 1)

        # Pipeline Status
        pipe_x = 10
        pipe_y = base_y + 180
        cv2.putText(dashboard, "PIPELINE STATUS", (pipe_x, pipe_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(dashboard, "CAMERA", (pipe_x, pipe_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(dashboard, "->", (pipe_x + 90, pipe_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(dashboard, "PERCEPTION", (pipe_x + 130, pipe_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(dashboard, "->", (pipe_x + 245, pipe_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(dashboard, "TRAVERSABILITY", (pipe_x + 280, pipe_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # ----------------------------------------------------
        # End-to-End FPS calculation
        # ----------------------------------------------------
        current_time = time.perf_counter()
        instant_fps = 1.0 / max(current_time - loop_start_time, 1e-6)
        end_to_end_fps = 0.9 * end_to_end_fps + 0.1 * instant_fps

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------
        cv2.imshow("SIH 26126 - UGV Perception Dashboard", dashboard)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

# ============================================================
# CLEANUP
# ============================================================
cap.release()
cv2.destroyAllWindows()
print("\nCamera segmentation dashboard stopped.")
