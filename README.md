# SIH 226126

Vision-Based Autonomous Navigation for UGV — PS26126 / Bharat Electronics Limited

Current phase: Perception + dataset + model training.

Canonical pipeline:
Camera → Segmentation → Navigability Groups → BEV/Costmap → Visual Odometry → A* → Pure Pursuit → Rover

Do not start frontend/dashboard work until the core perception model and navigation pipeline are validated.
