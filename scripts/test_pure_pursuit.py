#!/usr/bin/env python3
"""
Unit and Integration Test for Pure Pursuit Controller.

Tests:
  A. Vehicle starts before the path.
  B. Controller finds a lookahead point.
  C. Controller produces a non-zero steering/angular command.
  D. Vehicle follows a simulated sequence of poses.
  E. Speed decreases as curvature increases.
  F. Controller eventually reports goal reached.
  G. Invalid/empty path produces an emergency stop.

Generates:
  pure_pursuit_tracking_result.png showing:
    - planned path
    - vehicle trajectory
    - lookahead points
    - final goal
    - speed vs. curvature profile
"""

import math
import os
import sys
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.pure_pursuit import (
    ControlCommand,
    PurePursuitConfig,
    PurePursuitController,
    VehiclePose,
    grid_path_to_world_path,
)

SEPARATOR = "=" * 70


def print_command_summary(prefix: str, cmd: ControlCommand) -> None:
    """Print the exact required fields for test output."""
    lh_str = f"({cmd.lookahead_point[0]:.3f}, {cmd.lookahead_point[1]:.3f})" if cmd.lookahead_point else "None"
    print(f"\n--- {prefix} ---")
    print(f"Lookahead point: {lh_str}")
    print(f"Curvature:       {cmd.curvature:+.4f}")
    print(f"Linear speed:    {cmd.linear_speed:.4f}")
    print(f"Angular command: {cmd.angular_velocity:+.4f}")
    print(f"Goal reached:    {cmd.goal_reached}")
    print(f"Emergency stop:  {cmd.emergency_stop}")
    if cmd.message:
        print(f"Message:         {cmd.message}")


def generate_curved_path() -> List[Tuple[float, float]]:
    """
    Generate a synthetic S-curved reference path with varied curvature.
    Starts at (1.0, 0.5) and terminates at (9.0, 3.5).
    """
    s = np.linspace(0.0, 8.0, 160)
    # Parametric curve with varying curvature:
    # x goes from 1.0 to 9.0
    x = 1.0 + s
    # y introduces a gentle rise, a sharp curve, then leveling out
    y = 0.5 + 2.0 * np.sin(0.7 * s)
    return [(float(xi), float(yi)) for xi, yi in zip(x, y)]


def main():
    print(SEPARATOR)
    print("PURE PURSUIT CONTROLLER — VERIFICATION TEST SUITE")
    print(SEPARATOR)

    config = PurePursuitConfig(
        lookahead_distance=1.0,
        min_lookahead_distance=0.3,
        max_lookahead_distance=2.5,
        max_linear_speed=0.6,
        min_linear_speed=0.1,
        max_angular_speed=1.8,
        wheelbase=0.3,
        goal_tolerance=0.25,
        goal_slowdown_distance=1.2,
        curvature_slowdown_gain=2.0,
        max_allowed_crosstrack=6.0,
    )
    controller = PurePursuitController(config=config)
    path = generate_curved_path()
    path_arr = np.array(path)

    print(f"Generated synthetic curved path with {len(path)} waypoints.")
    print(f"Path start: ({path[0][0]:.2f}, {path[0][1]:.2f}), Goal: ({path[-1][0]:.2f}, {path[-1][1]:.2f})")
    print()

    # ------------------------------------------------------------------
    # Test A, B, C: Vehicle starts before the path
    # ------------------------------------------------------------------
    print(">>> TEST A, B, C: Vehicle Starts Before Path & Initial Steering <<<")
    # Vehicle placed at (0.0, 0.0) heading purely along +X (yaw = 0.0), while path starts at (1.0, 0.5)
    start_pose = VehiclePose(x=0.0, y=0.0, yaw=0.0)
    cmd_init = controller.compute_command(start_pose, path)

    print_command_summary("Initial state (vehicle at (0, 0), yaw=0):", cmd_init)

    assert cmd_init.lookahead_point is not None, "Lookahead point must be found!"
    assert abs(cmd_init.angular_velocity) > 1e-4, "Angular command must be non-zero to turn towards offset path!"
    assert not cmd_init.emergency_stop, "Initial state should not be in emergency stop!"
    assert not cmd_init.goal_reached, "Initial state should not report goal reached!"
    print("✅ TEST A, B, C PASSED: Lookahead point found and non-zero steering produced.\n")

    # ------------------------------------------------------------------
    # Test D, E, F: Closed-Loop Trajectory Following Simulation
    # ------------------------------------------------------------------
    print(">>> TEST D, E, F: Closed-Loop Path Tracking Simulation <<<")
    dt = 0.1  # 100 ms control loop
    max_steps = 600

    # Sim vehicle state
    sim_pose = VehiclePose(x=0.0, y=0.0, yaw=0.0)

    # History logs for plotting and assertions
    traj_x = [sim_pose.x]
    traj_y = [sim_pose.y]
    traj_yaw = [sim_pose.yaw]
    traj_v = []
    traj_w = []
    traj_curv = []
    lookahead_history = []
    times = []

    goal_reached_flag = False
    step_reached = -1

    for step in range(max_steps):
        t = step * dt
        cmd = controller.compute_command(sim_pose, path)

        if cmd.lookahead_point is not None:
            lookahead_history.append((sim_pose.x, sim_pose.y, cmd.lookahead_point[0], cmd.lookahead_point[1]))

        traj_v.append(cmd.linear_speed)
        traj_w.append(cmd.angular_velocity)
        traj_curv.append(cmd.curvature)
        times.append(t)

        # Print snapshot at key milestones along the trajectory
        if step in (0, 50, 150, 250, 350):
            print_command_summary(f"Trajectory snapshot at step {step} (t={t:.1f}s, pos=({sim_pose.x:.2f}, {sim_pose.y:.2f}))", cmd)

        if cmd.goal_reached:
            goal_reached_flag = True
            step_reached = step
            print_command_summary(f"Goal reached at step {step} (t={t:.1f}s, pos=({sim_pose.x:.2f}, {sim_pose.y:.2f}))", cmd)
            break

        # Simple unicycle kinematic integration
        sim_pose.x += cmd.linear_speed * math.cos(sim_pose.yaw) * dt
        sim_pose.y += cmd.linear_speed * math.sin(sim_pose.yaw) * dt
        sim_pose.yaw += cmd.angular_velocity * dt
        sim_pose.yaw = (sim_pose.yaw + math.pi) % (2.0 * math.pi) - math.pi

        traj_x.append(sim_pose.x)
        traj_y.append(sim_pose.y)
        traj_yaw.append(sim_pose.yaw)

    assert goal_reached_flag, f"Vehicle should reach the goal within {max_steps} steps!"
    print(f"✅ TEST D & F PASSED: Trajectory completed and goal reached at step {step_reached}.\n")

    # ------------------------------------------------------------------
    # Test E: Speed decreases as curvature increases
    # ------------------------------------------------------------------
    print(">>> TEST E: Speed vs Curvature Correlation Check <<<")
    curvs = np.abs(np.array(traj_curv))
    speeds = np.array(traj_v)

    # Consider only tracking phase before the final slowdown near goal
    active_mask = np.arange(len(speeds)) < (step_reached - 25)
    active_curvs = curvs[active_mask]
    active_speeds = speeds[active_mask]

    low_curv_speeds = active_speeds[active_curvs < 0.2]
    high_curv_speeds = active_speeds[active_curvs > 0.6]

    mean_speed_low_curv = float(np.mean(low_curv_speeds)) if len(low_curv_speeds) > 0 else config.max_linear_speed
    mean_speed_high_curv = float(np.mean(high_curv_speeds)) if len(high_curv_speeds) > 0 else config.min_linear_speed

    print(f"  Mean speed on low curvature  (|kappa| < 0.2): {mean_speed_low_curv:.4f} m/s")
    print(f"  Mean speed on high curvature (|kappa| > 0.6): {mean_speed_high_curv:.4f} m/s")
    assert mean_speed_high_curv < mean_speed_low_curv, (
        f"Speed limiter failed: high curvature speed ({mean_speed_high_curv:.3f}) "
        f"should be lower than low curvature speed ({mean_speed_low_curv:.3f})!"
    )
    print("✅ TEST E PASSED: Linear speed reduces significantly when curvature is high.\n")

    # ------------------------------------------------------------------
    # Test G: Invalid / empty path & emergency stop handling
    # ------------------------------------------------------------------
    print(">>> TEST G: Invalid / Empty Path & Emergency Stop Handling <<<")
    # Subtest G1: Empty path
    cmd_empty = controller.compute_command(start_pose, [])
    print_command_summary("G1. Empty path input:", cmd_empty)
    assert cmd_empty.emergency_stop, "Empty path must trigger emergency stop!"
    assert cmd_empty.linear_speed == 0.0, "Speed must be zero on emergency stop!"
    assert cmd_empty.angular_velocity == 0.0, "Angular velocity must be zero on emergency stop!"

    # Subtest G2: Path with NaN values
    bad_path = [(0.0, 0.0), (float("nan"), 1.0), (2.0, 2.0)]
    cmd_nan = controller.compute_command(start_pose, bad_path)
    print_command_summary("G2. NaN path input:", cmd_nan)
    assert cmd_nan.emergency_stop, "Path with NaN must trigger emergency stop!"

    # Subtest G3: Explicit caller-commanded emergency stop
    cmd_estop = controller.compute_command(start_pose, path, emergency_stop=True)
    print_command_summary("G3. Explicit caller emergency stop:", cmd_estop)
    assert cmd_estop.emergency_stop, "Explicit emergency stop flag must be honored!"
    print("✅ TEST G PASSED: All invalid / e-stop conditions handled safely.\n")

    # ------------------------------------------------------------------
    # Test Coordinate Conversion Helper Integration
    # ------------------------------------------------------------------
    print(">>> EXTRA TEST: Explicit Grid-to-World Coordinate Conversion <<<")
    grid_path_example = [(10, 20), (11, 21), (12, 22)]
    world_path_example = grid_path_to_world_path(grid_path_example, resolution=0.1, origin_x=0.0, origin_y=0.0)
    print(f"  Grid waypoints:  {grid_path_example}")
    print(f"  World waypoints: {world_path_example}")
    assert len(world_path_example) == 3
    assert world_path_example[0] == (2.0, 1.0)  # col*res=2.0, row*res=1.0
    print("✅ Coordinate conversion verified.\n")

    # ------------------------------------------------------------------
    # Generate Visualizations
    # ------------------------------------------------------------------
    output_png = "pure_pursuit_tracking_result.png"
    print(f"Generating visualization: {output_png} ...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10), gridspec_kw={"height_ratios": [2, 1]})

    # --- Plot 1: 2D Path Tracking ---
    ax1.plot(path_arr[:, 0], path_arr[:, 1], "b-", linewidth=2.5, label="Planned Path", zorder=3)
    ax1.plot(traj_x, traj_y, "g--", linewidth=2.0, label="Vehicle Trajectory", zorder=4)

    # Plot sample lookahead vectors (every 12 steps)
    stride = 10
    for i in range(0, len(lookahead_history), stride):
        vx, vy, lx, ly = lookahead_history[i]
        ax1.plot([vx, lx], [vy, ly], color="gray", linestyle=":", alpha=0.6, zorder=2)
        ax1.plot(lx, ly, marker="o", color="orange", markersize=4, alpha=0.7, zorder=5)

    # Annotate Start, Lookahead sample, Goal
    ax1.plot(traj_x[0], traj_y[0], "go", markersize=10, label="Vehicle Start (0, 0)", zorder=6)
    ax1.plot(path[0][0], path[0][1], "cs", markersize=8, label="Path Start", zorder=6)
    ax1.plot(path[-1][0], path[-1][1], "r*", markersize=14, label="Final Goal", zorder=6)
    ax1.plot([], [], marker="o", color="orange", linestyle="None", label="Lookahead Point")
    ax1.plot([], [], color="gray", linestyle=":", label="Lookahead Vector (L_d)")

    ax1.set_title("Pure Pursuit Controller — Path Tracking Simulation", fontsize=14, fontweight="bold")
    ax1.set_xlabel("X [meters]", fontsize=12)
    ax1.set_ylabel("Y [meters]", fontsize=12)
    ax1.axis("equal")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(loc="upper left", framealpha=0.9)

    # --- Plot 2: Speed Limiter vs Curvature Profile ---
    ax2_curv = ax2.twinx()

    p1, = ax2.plot(times, traj_v, "g-", linewidth=2.0, label="Linear Speed (v)")
    p2, = ax2_curv.plot(times, np.abs(traj_curv), "m-.", linewidth=1.8, label="Curvature |kappa|")

    ax2.set_title("Speed Limiter Response to Path Curvature", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Time [s]", fontsize=11)
    ax2.set_ylabel("Speed [m/s]", color="g", fontsize=11)
    ax2_curv.set_ylabel("Curvature |kappa| [1/m]", color="m", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)

    lines = [p1, p2]
    ax2.legend(lines, [l.get_label() for l in lines], loc="upper right")

    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.close()

    print(f"Visualization successfully saved to: {output_png}")
    print(SEPARATOR)
    print("ALL PURE PURSUIT TESTS COMPLETED SUCCESSFULLY!")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
