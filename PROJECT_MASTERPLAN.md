# SIS 226127 — Project Masterplan

## 0. Mission
Build a camera-first autonomous navigation prototype for a UGV that can operate without GPS, understand outdoor terrain, estimate its movement visually, construct a traversability costmap, plan a route, detect a newly blocked route, replan, and drive a small physical rover prototype.

## 1. Source-of-truth architecture
Camera → SegFormer-B0 → 6 navigability groups → ground-plane BEV → traversability costmap → OpenCV visual odometry → rolling global costmap → A* → Pure Pursuit + speed limiter + e-stop → rover.

Fallbacks:
- SegFormer-B0 → BiSeNetV2 / pretrained segmentation + class mapping
- OpenCV VO → ORB-SLAM3 stereo adapter
- Webots → custom/recorded simulation
- React dashboard → static HTML/canvas

## 2. Navigability classes
Six groups from the project plan:
1. Smooth
2. Rough
3. Bumpy
4. Forbidden
5. Obstacle
6. Background

Unknown/low-confidence is handled as a confidence/cost state rather than a seventh model class.

## 3. Data
Primary public training data:
- RUGD
- RELLIS-3D

Project-specific data:
- 10–20 minutes phone/outdoor footage
- 2–3 lighting conditions
- staged rocks/boxes/bags
- 50–100 manually labeled frames reserved as a domain-shift test set

Never split adjacent frames randomly. Split by sequence/scene.

## 4. Model
SegFormer-B0 pretrained checkpoint, fine-tuned; never train from scratch.

Input target: 512×512 or 640×512 depending GPU benchmark.
Batch size: choose the largest stable batch fitting GPU; start at 4 and use gradient accumulation if needed.
Optimizer: AdamW.
Initial LR: 6e-5 starting point; tune only if validation stalls/diverges.
Epoch budget: 40–60 with early stopping patience 8.
Loss: weighted cross-entropy; add class weighting only after measuring class imbalance.
Augmentations: brightness/contrast, blur, noise, scale/crop, horizontal flip, shadows.

## 5. Training run protocol
Run 0 — smoke test:
- 200–500 images
- 1 epoch
- prove dataloader, labels, forward pass, loss, checkpoint, visualization.

Run 1 — baseline:
- RUGD only
- official train/val split
- 30 epochs max, early stopping patience 5
- record mIoU, per-class IoU, pixel accuracy, FPS.

Run 2 — combined model:
- RUGD + RELLIS-3D
- 40–60 epochs max, early stopping patience 8
- same evaluation protocol.

Run 3 — imbalance/augmentation experiment:
- same combined data
- class-weighted loss OR stronger augmentation, not both initially
- 40–60 epochs max.

Run 4 — final candidate:
- take the best configuration from Runs 2–3
- 60 epochs max, early stopping patience 8
- save best validation checkpoint, not simply last epoch.

Run 5–7 — reproducibility:
- repeat the final configuration with seeds 42, 43, 44.
- report mean and spread across seeds.

Total: 1 smoke + 1 baseline + 2 candidate experiments + 3 final-seed runs = 7 training executions, with the smoke run not counted as a model result.

## 6. Model acceptance gate
Do not move to navigation integration until:
- validation loss is stable
- no class is completely collapsing without investigation
- qualitative masks look correct on RUGD test scenes
- model works on held-out RELLIS scenes
- model works on the 50–100-frame own-footage domain-shift set
- inference latency is measured on the actual machine

No invented accuracy target. Acceptance is based on measured results and failure analysis.

## 7. Test suite
A. Clear path
B. Static obstacle
C. Sudden obstacle
D. Poor lighting
E. Difficult terrain
F. Localization challenge
G. No valid route

Run each navigation scenario at least 10 times after the pipeline is stable, using different obstacle placements/seeds where applicable.

## 8. Navigation build order
1. Segmentation inference
2. Class→group conversion
3. Ground-plane projection / BEV
4. Costmap
5. A* on costmap
6. Fixed-path controller
7. OpenCV VO + tracking quality
8. Fuse BEV + pose into rolling costmap
9. Closed-loop simulated rover
10. Obstacle insertion
11. Path invalidation
12. A* replan
13. Confidence gating + safe stop
14. Real phone-camera footage
15. Physical toy rover

## 9. Physical prototype
Phone mounted on rover is the camera.
Laptop runs the heavy perception/planning stack.
Rover receives velocity/steering commands through a simple control interface.

The physical prototype is not the first milestone. It is the final embodiment after the software loop works in simulation and on recorded video.

## 10. Logs
Every frame/event should be timestamped. Minimum fields:
- frame_id
- timestamp
- segmentation confidence
- pose x/y/yaw
- tracking quality
- current goal
- path length
- path cost
- minimum clearance
- replan reason
- replan latency
- commanded v/w
- safety state

## 11. Frontend
Deferred until core pipeline works.
Later stack:
FastAPI + WebSocket backend
React + Vite frontend
Panels: raw camera, segmentation, costmap, localization, planner, rover state, event/explanation log.

## 12. Non-goals for first build
No LiDAR dependency.
No production-grade autonomy claim.
No novel SLAM algorithm.
No training from scratch.
No massive custom dataset before baseline works.
No React polish before navigation works.
No ORB-SLAM3 integration before OpenCV VO works.

## 13. Final demonstration target
GPS OFF.
Rover starts at A.
Camera sees terrain.
Segmentation updates.
Costmap forms.
Localization tracks motion.
A* produces route.
Obstacle appears.
Route becomes invalid.
System stops/slows safely, replans, explains the reason, and continues to B.
