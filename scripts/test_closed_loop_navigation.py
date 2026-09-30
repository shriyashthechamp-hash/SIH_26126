#!/usr/bin/env python3
"""
Test script for Closed-Loop Autonomous Navigation Simulation.

Executes an end-to-end integration scenario:
  1. Synthetic 2D outdoor environment with traversable, rough, and obstacle terrain.
  2. Vehicle starts at START and navigates towards GOAL.
  3. TraversabilityCostmap processes terrain into costmap and blocked_mask.
  4. AStarPlanner computes the initial optimal path through the primary corridor.
  5. Pure Pursuit controller steers the vehicle along the path.
  6. At a deterministic step, a dynamic obstacle blocks the primary corridor.
  7. path_validator detects the blockage and invalidates the path.
  8. AStarPlanner dynamically replans through an alternate corridor.
  9. Vehicle safely follows the replanned route and reaches GOAL.
  10. Telemetry and timeline visualizations are generated.
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.simulation.navigation_simulator import NavigationSimulator

SEPARATOR = "=" * 70


def generate_visualizations(sim: NavigationSimulator, summary, logs, output_dir: Path) -> None:
    """Generate both required visual artifact plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    res = sim.resolution

    # ------------------------------------------------------------------
    # Plot 1: outputs/closed_loop_navigation_result.png
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 10))

    # Get final costmap from environment for background display
    obs_mask = sim.environment.get_observation()
    trav_res = sim.traversability.process(obs_mask)
    costmap = trav_res.costmap

    # Display costmap as background (extent in metric meters: [xmin, xmax, ymin, ymax])
    # col maps to x, row maps to y
    extent = [0.0, sim.environment.cols * res, sim.environment.rows * res, 0.0]
    cax = ax.imshow(
        costmap,
        cmap="YlOrRd",
        origin="upper",
        extent=extent,
        alpha=0.65,
        vmin=0.0,
        vmax=1.0,
    )
    cbar = plt.colorbar(cax, ax=ax, fraction=0.035, pad=0.04)
    cbar.set_label("Traversability Cost [0.0 = Smooth, 1.0 = Blocked]", fontsize=11)

    # Highlight static obstacles
    static_mask = np.zeros_like(sim.environment.mask, dtype=bool)
    static_mask[0:6, 48:52] = True     # upper wall
    static_mask[28:36, 48:52] = True   # island wall
    static_mask[46:80, 48:52] = True   # lower wall
    ax.imshow(
        np.ma.masked_where(~static_mask, static_mask),
        cmap="gray",
        origin="upper",
        extent=extent,
        alpha=0.85,
    )

    # Highlight Dynamic Obstacle (sealed primary corridor: rows 35..47, cols 47..53)
    dyn_mask = np.zeros_like(sim.environment.mask, dtype=bool)
    dyn_mask[35:47, 47:53] = True
    ax.imshow(
        np.ma.masked_where(~dyn_mask, dyn_mask),
        cmap="Reds",
        origin="upper",
        extent=extent,
        alpha=0.9,
    )

    # Plot initial planned path (ghosted/dashed salmon)
    if sim.initial_world_path:
        init_pts = np.array(sim.initial_world_path)
        ax.plot(
            init_pts[:, 0],
            init_pts[:, 1],
            color="#FF6B6B",
            linestyle="--",
            linewidth=2.5,
            label="Initial Path (Blocked)",
            zorder=4,
        )

    # Plot replanned path (cyan)
    if sim.replanned_world_path:
        replan_pts = np.array(sim.replanned_world_path)
        ax.plot(
            replan_pts[:, 0],
            replan_pts[:, 1],
            color="#00C9A7",
            linestyle="-",
            linewidth=2.5,
            label="Replanned Path (Alternate)",
            zorder=5,
        )

    # Plot actual vehicle trajectory (dark blue with markers)
    traj = np.array(sim.vehicle_trajectory)
    ax.plot(
        traj[:, 0],
        traj[:, 1],
        color="#1B1464",
        linestyle="-",
        linewidth=2.8,
        label="Vehicle Trajectory",
        zorder=6,
    )

    # Heading arrows along trajectory (sample every 20 steps)
    stride = 25
    for i in range(0, len(logs), stride):
        entry = logs[i]
        dx = 0.35 * np.cos(entry.yaw)
        dy = 0.35 * np.sin(entry.yaw)
        ax.arrow(
            entry.x,
            entry.y,
            dx,
            dy,
            head_width=0.15,
            head_length=0.12,
            fc="#0652DD",
            ec="#0652DD",
            zorder=7,
        )

    # Replan point marker
    replan_logs = [log for log in logs if log.replanning_occurred and log.path_id > 1]
    if replan_logs:
        replan_pt = replan_logs[0]
        ax.scatter(
            replan_pt.x,
            replan_pt.y,
            color="#FF9F1A",
            s=180,
            marker="X",
            label=f"Replan Point (t={replan_pt.time_sec:.1f}s)",
            zorder=8,
        )

    # Start, Goal, and Final positions
    ax.plot(
        sim.start_world[0],
        sim.start_world[1],
        marker="o",
        color="#2ED573",
        markersize=12,
        markeredgecolor="black",
        label="START",
        zorder=9,
    )
    ax.plot(
        sim.goal_world[0],
        sim.goal_world[1],
        marker="*",
        color="#FF4757",
        markersize=18,
        markeredgecolor="black",
        label="GOAL",
        zorder=9,
    )
    ax.plot(
        traj[-1, 0],
        traj[-1, 1],
        marker="P",
        color="#FFA502",
        markersize=12,
        markeredgecolor="black",
        label=f"Final Rover Pose ({traj[-1, 0]:.2f}, {traj[-1, 1]:.2f})",
        zorder=10,
    )

    # Dynamic obstacle annotation
    dyn_x = 5.0  # col 50 * 0.1
    dyn_y = 4.0  # row 40 * 0.1
    ax.text(
        dyn_x + 0.3,
        dyn_y,
        "Dynamic Obstacle\n(Injected at step 40)",
        color="#D63031",
        fontsize=9,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D63031", alpha=0.9),
        zorder=10,
    )

    # Alternate corridor annotation
    ax.text(
        dyn_x - 1.2,
        2.0,
        "Alternate\nCorridor",
        color="#0984E3",
        fontsize=9,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#0984E3", alpha=0.9),
        zorder=10,
    )

    ax.set_title(
        "Closed-Loop Autonomous Navigation — Dynamic Replanning & Pursuit",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("X Position [meters]", fontsize=12)
    ax.set_ylabel("Y Position [meters]", fontsize=12)
    ax.set_xlim(-0.2, sim.environment.cols * res + 0.2)
    ax.set_ylim(sim.environment.rows * res + 0.2, -0.2)  # Inverted Y for image/matrix convention
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", framealpha=0.92, fontsize=10)

    result_path = output_dir / "closed_loop_navigation_result.png"
    plt.tight_layout()
    plt.savefig(result_path, dpi=160)
    plt.close()
    print(f"Saved: {result_path}")

    # ------------------------------------------------------------------
    # Plot 2: outputs/closed_loop_navigation_timeline.png
    # ------------------------------------------------------------------
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    times = [log.time_sec for log in logs]
    speeds = [log.linear_speed for log in logs]
    distances = [log.distance_to_goal for log in logs]
    replan_times = [log.time_sec for log in logs if log.replanning_occurred and log.path_id > 1]
    obs_active_times = [log.time_sec for log in logs if log.obstacle_present]

    # Panel 1: Vehicle Linear Speed
    ax1.plot(times, speeds, color="#2ED573", linewidth=2.2, label="Linear Speed (v)")
    for rt in replan_times:
        ax1.axvline(rt, color="#FF9F1A", linestyle="--", linewidth=1.8, label="Replan Triggered")
    if obs_active_times:
        ax1.axvspan(obs_active_times[0], times[-1], color="#FF6B6B", alpha=0.12, label="Obstacle Active")
    ax1.set_ylabel("Speed [m/s]", fontsize=11)
    ax1.set_title("Navigation Telemetry Timeline", fontsize=13, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Panel 2: Distance to Goal
    ax2.plot(times, distances, color="#3742FA", linewidth=2.2, label="Distance to Goal")
    ax2.axhline(0.25, color="gray", linestyle=":", label="Goal Tolerance (0.25m)")
    for rt in replan_times:
        ax2.axvline(rt, color="#FF9F1A", linestyle="--", linewidth=1.8)
    if obs_active_times:
        ax2.axvspan(obs_active_times[0], times[-1], color="#FF6B6B", alpha=0.12)
    ax2.set_ylabel("Distance [m]", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right", framealpha=0.9)

    # Panel 3: Path ID & Replanning Events
    path_ids = [log.path_id for log in logs]
    ax3.step(times, path_ids, color="#70A1FF", linewidth=2.0, where="post", label="Active Path ID")
    for rt in replan_times:
        ax3.axvline(rt, color="#FF9F1A", linestyle="--", linewidth=1.8, label="Replanning Event")
    if obs_active_times:
        ax3.axvspan(obs_active_times[0], times[-1], color="#FF6B6B", alpha=0.12, label="Obstacle Active")
    ax3.set_ylabel("Path Generation ID", fontsize=11)
    ax3.set_xlabel("Simulation Time [seconds]", fontsize=11)
    ax3.set_yticks([1, 2])
    ax3.set_yticklabels(["Path 1 (Initial)", "Path 2 (Replanned)"])
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="lower right", framealpha=0.9)

    timeline_path = output_dir / "closed_loop_navigation_timeline.png"
    plt.tight_layout()
    plt.savefig(timeline_path, dpi=160)
    plt.close()
    print(f"Saved: {timeline_path}")


def main():
    print(SEPARATOR)
    print("CLOSED-LOOP AUTONOMOUS NAVIGATION SIMULATION")
    print(SEPARATOR)

    sim = NavigationSimulator(
        dt=0.1,
        max_steps=500,
        dynamic_obstacle_step=40,
        resolution=0.1,
        start_grid=(40, 10),
        goal_grid=(40, 90),
    )

    summary, logs = sim.run()

    print()
    summary.print_summary()
    print()

    # Generate visual artifacts
    output_dir = Path("outputs")
    generate_visualizations(sim, summary, logs, output_dir)

    # Evaluation of pass conditions
    pass_condition = (
        summary.initial_path_found
        and summary.dynamic_obstacle_detected
        and summary.path_invalidated
        and summary.new_path_generated
        and summary.goal_reached
        and not summary.emergency_stop
    )

    print()
    print(SEPARATOR)
    if pass_condition:
        print("Closed-loop navigation simulation: PASS")
    else:
        print("Closed-loop navigation simulation: FAIL")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
