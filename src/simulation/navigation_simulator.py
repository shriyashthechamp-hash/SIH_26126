"""
Closed-loop Autonomous Navigation Simulator for SIH 26126 Rover.

Orchestrates verified modules:
  - TraversabilityCostmap (perception / traversability layer)
  - costmap_adapter (adapter layer)
  - AStarPlanner (global path planner)
  - path_validator (runtime safety & replan trigger)
  - PurePursuitController (motion control layer)
  - SimulatedVehicle (unicycle kinematics)

Disclaimer:
  Engineering integration simulation for autonomous architecture validation.
  Not calibrated for physical hardware dynamics or metric camera accuracy.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import verified pipeline modules
from src.traversability.costmap import TraversabilityCostmap, TraversabilityResult
from src.planning.costmap_adapter import get_planning_arrays
from src.planning.astar import AStarPlanner
from src.planning.path_validator import validate_path, ValidationResult
from src.control.pure_pursuit import (
    ControlCommand,
    PurePursuitConfig,
    PurePursuitController,
    VehiclePose,
    grid_to_world,
    world_to_grid,
    grid_path_to_world_path,
)


# ---------------------------------------------------------------------------
# Vehicle Kinematics Model
# ---------------------------------------------------------------------------

@dataclass
class SimulatedVehicle:
    """
    Planar unicycle ground vehicle kinematic model.
    Designed so a Webots interface or physical rover CAN/serial adapter
    can drop in as a replacement without altering the navigation pipeline.
    """
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    linear_speed: float = 0.0
    angular_velocity: float = 0.0

    def step(self, cmd_linear_speed: float, cmd_angular_velocity: float, dt: float) -> None:
        """Advance vehicle state using unicycle kinematic integration."""
        self.linear_speed = float(cmd_linear_speed)
        self.angular_velocity = float(cmd_angular_velocity)

        self.x += self.linear_speed * math.cos(self.yaw) * dt
        self.y += self.linear_speed * math.sin(self.yaw) * dt
        self.yaw += self.angular_velocity * dt
        self.yaw = (self.yaw + math.pi) % (2.0 * math.pi) - math.pi

    @property
    def pose(self) -> VehiclePose:
        return VehiclePose(x=self.x, y=self.y, yaw=self.yaw)


# ---------------------------------------------------------------------------
# Synthetic Environment
# ---------------------------------------------------------------------------

class SyntheticEnvironment:
    """
    2D outdoor synthetic grid environment containing:
      - Smooth traversable ground (class 0)
      - Rough terrain patches (class 1)
      - Bumpy terrain patches (class 2)
      - Static obstacle barrier with primary and alternate corridors (class 4)
      - Dynamic obstacle capability to seal the primary corridor at runtime
    """

    def __init__(
        self,
        rows: int = 80,
        cols: int = 100,
        resolution: float = 0.1,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.resolution = resolution
        self.origin_x = origin_x
        self.origin_y = origin_y

        self.mask = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.dynamic_obstacle_active = False
        self._build_static_environment()

    def _build_static_environment(self) -> None:
        """Initialize the static landscape with varied terrain and two corridors."""
        self.mask.fill(0)  # Class 0: Smooth (cost 0.0)

        # Patch of Rough terrain (Class 1, cost 0.3)
        self.mask[4:18, 65:85] = 1

        # Patch of Bumpy terrain (Class 2, cost 0.6)
        self.mask[55:72, 15:40] = 2

        # Central obstacle barrier (Class 4, cost 1.0) along cols 48:52
        # Upper wall: rows 0 to 6
        self.mask[0:6, 48:52] = 4
        # Island barrier between alternate & primary corridors: rows 28 to 36
        self.mask[28:36, 48:52] = 4
        # Lower wall: rows 46 to 80
        self.mask[46:self.rows, 48:52] = 4
        # Primary corridor: rows 36 to 46 (width 1.0 m, direct route along row 40)
        # Alternate corridor: rows 6 to 28 (width 2.2 m, wide safe detour)

    def spawn_dynamic_obstacle(self) -> None:
        """Block the primary corridor with a sudden obstacle."""
        if not self.dynamic_obstacle_active:
            # Seal primary corridor: rows 35 to 47, cols 47 to 53
            self.mask[35:47, 47:53] = 4
            self.dynamic_obstacle_active = True

    def get_observation(self) -> np.ndarray:
        """Return the current ground truth segmentation mask."""
        return self.mask.copy()


# ---------------------------------------------------------------------------
# Telemetry Logging & Summary
# ---------------------------------------------------------------------------

@dataclass
class TelemetryLog:
    """Record of navigation state at a single simulation timestep."""
    timestep: int
    time_sec: float
    x: float
    y: float
    yaw: float
    path_id: int
    replanning_occurred: bool
    obstacle_present: bool
    linear_speed: float
    angular_velocity: float
    distance_to_goal: float


@dataclass
class SimulationSummary:
    """Final summary of the closed-loop navigation simulation."""
    simulation_completed: bool = False
    goal_reached: bool = False
    total_steps: int = 0
    total_replans: int = 0
    initial_path_found: bool = False
    dynamic_obstacle_detected: bool = False
    path_invalidated: bool = False
    new_path_generated: bool = False
    emergency_stop: bool = False
    final_distance_to_goal: float = 0.0

    def print_summary(self) -> None:
        """Print the required formatted summary block."""
        print("SIMULATION SUMMARY:")
        print(f"Simulation completed: {'YES' if self.simulation_completed else 'NO'}")
        print(f"Goal reached: {'YES' if self.goal_reached else 'NO'}")
        print(f"Total steps: {self.total_steps}")
        print(f"Total replans: {self.total_replans}")
        print(f"Initial path found: {'YES' if self.initial_path_found else 'NO'}")
        print(f"Dynamic obstacle detected: {'YES' if self.dynamic_obstacle_detected else 'NO'}")
        print(f"Path invalidated: {'YES' if self.path_invalidated else 'NO'}")
        print(f"New path generated: {'YES' if self.new_path_generated else 'NO'}")
        print(f"Emergency stop: {'YES' if self.emergency_stop else 'NO'}")
        print(f"Final distance to goal: {self.final_distance_to_goal:.4f} m")


# ---------------------------------------------------------------------------
# Navigation Simulator
# ---------------------------------------------------------------------------

class NavigationSimulator:
    """
    Closed-loop Autonomous Navigation Simulator.

    Connects:
      Environment -> TraversabilityCostmap -> costmap_adapter ->
      AStarPlanner -> path_validator -> PurePursuitController -> SimulatedVehicle.
    """

    def __init__(
        self,
        dt: float = 0.1,
        max_steps: int = 600,
        dynamic_obstacle_step: int = 40,
        config_path: str = "configs/traversability.yaml",
        resolution: float = 0.1,
        start_grid: Tuple[int, int] = (40, 10),
        goal_grid: Tuple[int, int] = (40, 90),
    ) -> None:
        self.dt = dt
        self.max_steps = max_steps
        self.dynamic_obstacle_step = dynamic_obstacle_step
        self.resolution = resolution

        self.start_grid = start_grid
        self.goal_grid = goal_grid

        # World start & goal coordinates
        self.start_world = grid_to_world(start_grid[0], start_grid[1], resolution=resolution)
        self.goal_world = grid_to_world(goal_grid[0], goal_grid[1], resolution=resolution)

        # Core pipeline components
        self.environment = SyntheticEnvironment(rows=80, cols=100, resolution=resolution)
        self.traversability = TraversabilityCostmap(config_path=config_path)
        self.traversability.obstacle_inflation = 3

        pursuit_cfg = PurePursuitConfig(
            lookahead_distance=0.5,
            min_lookahead_distance=0.25,
            max_lookahead_distance=1.8,
            max_linear_speed=0.5,
            min_linear_speed=0.08,
            max_angular_speed=1.5,
            wheelbase=0.3,
            goal_tolerance=0.25,
            goal_slowdown_distance=1.0,
            curvature_slowdown_gain=1.8,
            max_allowed_crosstrack=3.0,
        )
        self.controller = PurePursuitController(config=pursuit_cfg)

        # Vehicle state (starts at start_world, heading along +X)
        self.vehicle = SimulatedVehicle(x=self.start_world[0], y=self.start_world[1], yaw=0.0)

        # Path tracking state
        self.current_grid_path: List[Tuple[int, int]] = []
        self.current_world_path: List[Tuple[float, float]] = []
        self.initial_world_path: List[Tuple[float, float]] = []
        self.replanned_world_path: List[Tuple[float, float]] = []
        self.path_id: int = 0

        # Status tracking
        self.summary = SimulationSummary()
        self.logs: List[TelemetryLog] = []
        self.vehicle_trajectory: List[Tuple[float, float]] = [(self.vehicle.x, self.vehicle.y)]

    def _plan_route(self, costmap: np.ndarray, blocked_mask: np.ndarray) -> bool:
        """Compute A* route from current vehicle grid position to goal."""
        cur_row, cur_col = world_to_grid(self.vehicle.x, self.vehicle.y, resolution=self.resolution)

        # Clamp start to valid grid boundaries
        cur_row = max(0, min(self.environment.rows - 1, cur_row))
        cur_col = max(0, min(self.environment.cols - 1, cur_col))

        planner = AStarPlanner(costmap=costmap, blocked_mask=blocked_mask)
        grid_path = planner.plan(start=(cur_row, cur_col), goal=self.goal_grid)

        if not grid_path:
            return False

        self.current_grid_path = grid_path
        self.current_world_path = grid_path_to_world_path(
            grid_path, resolution=self.resolution
        )
        self.path_id += 1

        if self.path_id == 1:
            self.initial_world_path = list(self.current_world_path)
            self.summary.initial_path_found = True
        else:
            self.replanned_world_path = list(self.current_world_path)
            self.summary.new_path_generated = True

        return True

    def run(self) -> Tuple[SimulationSummary, List[TelemetryLog]]:
        """
        Execute the closed-loop navigation simulation loop.
        """
        for step in range(self.max_steps):
            t = step * self.dt
            replanning_occurred = False

            # -------------------------------------------------------------
            # Dynamic Obstacle Injection at specified timestep
            # -------------------------------------------------------------
            if step == self.dynamic_obstacle_step:
                self.environment.spawn_dynamic_obstacle()
                self.summary.dynamic_obstacle_detected = True

            # 1. Observe synthetic environment
            obs_mask = self.environment.get_observation()

            # 2. Generate traversability costmap
            trav_result: TraversabilityResult = self.traversability.process(obs_mask)

            # 3. Produce costmap & blocked_mask
            costmap, blocked_mask = get_planning_arrays(trav_result)

            # 4. Check whether an initial path exists
            if not self.current_grid_path:
                plan_ok = self._plan_route(costmap, blocked_mask)
                if not plan_ok:
                    self.summary.emergency_stop = True
                    break
                replanning_occurred = True

            # 5. Validate current path against current environment
            # Extract remaining waypoints ahead of current vehicle position
            cur_pos = (self.vehicle.x, self.vehicle.y)
            path_pts = np.array(self.current_world_path)
            dists = np.hypot(path_pts[:, 0] - cur_pos[0], path_pts[:, 1] - cur_pos[1])
            closest_idx = int(np.argmin(dists))

            # Validate remaining waypoints from closest forward
            remaining_grid_path = self.current_grid_path[closest_idx:]
            val_result: ValidationResult = validate_path(
                remaining_grid_path, blocked_mask=blocked_mask, costmap=costmap
            )

            # 6. Replan if path is invalid
            if not val_result.valid:
                self.summary.path_invalidated = True
                plan_ok = self._plan_route(costmap, blocked_mask)
                if not plan_ok:
                    self.summary.emergency_stop = True
                    break
                self.summary.total_replans += 1
                replanning_occurred = True

            # 7. Run Pure Pursuit Controller
            dist_to_goal = math.hypot(
                self.goal_world[0] - self.vehicle.x, self.goal_world[1] - self.vehicle.y
            )

            cmd: ControlCommand = self.controller.compute_command(
                vehicle_pose=self.vehicle.pose,
                path=self.current_world_path,
                emergency_stop=self.summary.emergency_stop,
            )

            # 8. Apply command to vehicle unicycle kinematic model
            if cmd.emergency_stop:
                self.summary.emergency_stop = True
                break

            if cmd.goal_reached or dist_to_goal <= self.controller.config.goal_tolerance:
                self.summary.goal_reached = True
                self.summary.simulation_completed = True
                self.vehicle.step(0.0, 0.0, self.dt)
                self.vehicle_trajectory.append((self.vehicle.x, self.vehicle.y))

                # Log final step
                self.logs.append(
                    TelemetryLog(
                        timestep=step,
                        time_sec=t,
                        x=self.vehicle.x,
                        y=self.vehicle.y,
                        yaw=self.vehicle.yaw,
                        path_id=self.path_id,
                        replanning_occurred=replanning_occurred,
                        obstacle_present=self.environment.dynamic_obstacle_active,
                        linear_speed=0.0,
                        angular_velocity=0.0,
                        distance_to_goal=dist_to_goal,
                    )
                )
                break

            self.vehicle.step(cmd.linear_speed, cmd.angular_velocity, self.dt)
            self.vehicle_trajectory.append((self.vehicle.x, self.vehicle.y))

            # Log step telemetry
            self.logs.append(
                TelemetryLog(
                    timestep=step,
                    time_sec=t,
                    x=self.vehicle.x,
                    y=self.vehicle.y,
                    yaw=self.vehicle.yaw,
                    path_id=self.path_id,
                    replanning_occurred=replanning_occurred,
                    obstacle_present=self.environment.dynamic_obstacle_active,
                    linear_speed=self.vehicle.linear_speed,
                    angular_velocity=self.vehicle.angular_velocity,
                    distance_to_goal=dist_to_goal,
                )
            )

        self.summary.total_steps = len(self.logs)
        final_dist = math.hypot(
            self.goal_world[0] - self.vehicle.x, self.goal_world[1] - self.vehicle.y
        )
        self.summary.final_distance_to_goal = final_dist
        if self.summary.goal_reached:
            self.summary.simulation_completed = True

        return self.summary, self.logs
