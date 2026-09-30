"""
Pure Pursuit Path Tracking Controller for SIH 26126 Autonomous Rover.

Coordinate Conventions:
-----------------------
1. World / Metric Frame (Used by Controller & Localization):
   - 2D Cartesian plane: (x, y) coordinates in meters (or relative VO units).
   - Heading (yaw): in radians, where 0.0 rad points along the positive X axis.
   - Yaw increases counter-clockwise (positive yaw turns left).
   - Forward kinematics:
       dx/dt = v * cos(yaw)
       dy/dt = v * sin(yaw)
       dyaw/dt = omega

2. Grid / Planner Frame (Used by Traversability Costmap & A*):
   - 2D matrix indices: (row, col).
   - row: index from 0 to H-1 (downward in image/matrix coordinates).
   - col: index from 0 to W-1 (rightward in image/matrix coordinates).
   - IMPORTANT: (row, col) coordinates MUST be transformed to metric (x, y)
     using `grid_to_world()` or `grid_path_to_world_path()` before being passed
     to this controller. Do NOT pass raw grid row/col directly as metric (x, y).

3. Vehicle Body Frame:
   - Origin at vehicle reference center.
   - Forward axis: +x_local (aligned with heading).
   - Lateral axis: +y_local (left of vehicle).
   - Heading error alpha = atan2(y_local, x_local).
"""

from dataclasses import dataclass
import math
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np


# ---------------------------------------------------------------------------
# Coordinate Conversion Helpers
# ---------------------------------------------------------------------------

def grid_to_world(
    row: float,
    col: float,
    resolution: float = 0.05,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    swap_axes: bool = False,
) -> Tuple[float, float]:
    """
    Convert a single A* grid cell (row, col) to metric world coordinates (x, y).

    Parameters
    ----------
    row : float
        Grid row index.
    col : float
        Grid column index.
    resolution : float, default=0.05
        Meters per grid cell.
    origin_x : float, default=0.0
        World X coordinate corresponding to grid (row=0, col=0).
    origin_y : float, default=0.0
        World Y coordinate corresponding to grid (row=0, col=0).
    swap_axes : bool, default=False
        If True, maps row -> x and col -> y (e.g. forward row, lateral col).
        If False (default standard image/Cartesian mapping),
        maps col -> x (horizontal) and row -> y (vertical).

    Returns
    -------
    (x, y) : Tuple[float, float]
        Metric world coordinates.
    """
    if swap_axes:
        x = float(row * resolution + origin_x)
        y = float(col * resolution + origin_y)
    else:
        x = float(col * resolution + origin_x)
        y = float(row * resolution + origin_y)
    return (x, y)


def world_to_grid(
    x: float,
    y: float,
    resolution: float = 0.05,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    swap_axes: bool = False,
) -> Tuple[int, int]:
    """
    Convert metric world coordinates (x, y) to A* grid cell (row, col).
    """
    if swap_axes:
        row = int(round((x - origin_x) / resolution))
        col = int(round((y - origin_y) / resolution))
    else:
        col = int(round((x - origin_x) / resolution))
        row = int(round((y - origin_y) / resolution))
    return (row, col)


def grid_path_to_world_path(
    grid_path: Sequence[Tuple[int, int]],
    resolution: float = 0.05,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    swap_axes: bool = False,
) -> List[Tuple[float, float]]:
    """
    Convert a sequence of (row, col) A* grid waypoints into metric (x, y) coordinates.

    Parameters
    ----------
    grid_path : Sequence[Tuple[int, int]]
        List of (row, col) grid coordinates from AStarPlanner.
    resolution : float, default=0.05
        Meters per cell.
    origin_x : float, default=0.0
        Origin offset for world X.
    origin_y : float, default=0.0
        Origin offset for world Y.
    swap_axes : bool, default=False
        Axis mapping mode.

    Returns
    -------
    world_path : List[Tuple[float, float]]
        List of (x, y) coordinates in metric frame.
    """
    return [
        grid_to_world(
            r,
            c,
            resolution=resolution,
            origin_x=origin_x,
            origin_y=origin_y,
            swap_axes=swap_axes,
        )
        for (r, c) in grid_path
    ]


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class VehiclePose:
    """Vehicle pose in metric world frame."""
    x: float
    y: float
    yaw: float  # Radians, 0.0 = +X axis, counter-clockwise positive

    @classmethod
    def from_any(cls, pose: Any) -> "VehiclePose":
        """
        Create a VehiclePose from:
        - VehiclePose instance
        - Tuple / List: (x, y, yaw)
        - Object with .x, .y, .yaw attributes (e.g. PoseEstimate from visual_odometry)
        """
        if isinstance(pose, VehiclePose):
            return pose
        if isinstance(pose, (tuple, list)) and len(pose) >= 3:
            return cls(x=float(pose[0]), y=float(pose[1]), yaw=float(pose[2]))
        if hasattr(pose, "x") and hasattr(pose, "y") and hasattr(pose, "yaw"):
            return cls(x=float(pose.x), y=float(pose.y), yaw=float(pose.yaw))
        raise ValueError(
            f"Cannot convert pose of type {type(pose)} to VehiclePose. "
            "Expected (x, y, yaw) tuple or object with x, y, yaw attributes."
        )


@dataclass
class ControlCommand:
    """Control output produced by PurePursuitController."""
    linear_speed: float
    """Commanded forward speed (m/s or relative units/s)."""

    angular_velocity: float
    """Commanded yaw rate / turning speed (rad/s), positive = counter-clockwise (left)."""

    steering_angle: float
    """Equivalent front-wheel steering angle (rad) for Ackermann model."""

    curvature: float
    """Curvature kappa (1/m) of the pursuit arc."""

    lookahead_point: Optional[Tuple[float, float]]
    """World coordinates (x, y) of the target lookahead point on the path."""

    goal_reached: bool
    """True if vehicle is within goal_tolerance of the final path waypoint."""

    emergency_stop: bool
    """True if emergency stop triggered (invalid path, lost, or commanded)."""

    message: str = ""
    """Diagnostic status or reason."""

    # Convenience aliases
    @property
    def linear_velocity(self) -> float:
        return self.linear_speed

    @property
    def angular_command(self) -> float:
        return self.angular_velocity


@dataclass
class PurePursuitConfig:
    """Configuration parameters for PurePursuitController."""
    lookahead_distance: float = 1.0
    """Target lookahead distance L_d (meters)."""

    min_lookahead_distance: float = 0.3
    """Minimum allowable lookahead distance."""

    max_lookahead_distance: float = 3.0
    """Maximum allowable lookahead distance."""

    max_linear_speed: float = 0.5
    """Maximum forward speed (m/s)."""

    min_linear_speed: float = 0.05
    """Minimum non-zero forward speed when moving."""

    max_angular_speed: float = 1.5
    """Maximum turning rate (rad/s)."""

    wheelbase: float = 0.3
    """Vehicle wheelbase (meters) for steering angle calculation."""

    goal_tolerance: float = 0.25
    """Distance threshold to final waypoint to declare goal reached."""

    goal_slowdown_distance: float = 1.2
    """Distance from goal at which linear speed smoothly ramps down."""

    curvature_slowdown_gain: float = 1.5
    """Gain determining speed reduction on sharp curves (v = v_max / (1 + gain * |kappa|))."""

    max_allowed_crosstrack: Optional[float] = 5.0
    """Maximum distance from vehicle to closest path point before triggering e-stop."""


# ---------------------------------------------------------------------------
# Pure Pursuit Controller Implementation
# ---------------------------------------------------------------------------

class PurePursuitController:
    """
    Pure Pursuit Path Tracking Controller for planar ground vehicles.

    Computes steering and velocity commands to follow a metric 2D reference path
    given current vehicle pose estimation.

    Parameters
    ----------
    config : PurePursuitConfig, optional
        Tuning parameters. If None, default config is used.
    """

    def __init__(self, config: Optional[PurePursuitConfig] = None) -> None:
        self.config = config or PurePursuitConfig()

    def update_config(self, **kwargs) -> None:
        """Update controller configuration fields dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise AttributeError(f"PurePursuitConfig has no field '{key}'")

    @staticmethod
    def _wrap_to_pi(angle: float) -> float:
        """Normalize an angle to [-pi, pi]."""
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    def _validate_path(
        self,
        path: Optional[Sequence[Tuple[float, float]]],
    ) -> Tuple[bool, str, np.ndarray]:
        """
        Validate path format, emptiness, and numeric stability.
        """
        if path is None or len(path) == 0:
            return False, "Path is empty or None", np.empty((0, 2))

        try:
            arr = np.asarray(path, dtype=np.float64)
        except Exception as e:
            return False, f"Failed to parse path into float array: {e}", np.empty((0, 2))

        if arr.ndim != 2 or arr.shape[1] < 2:
            return False, f"Path must have shape (N, 2), got shape {arr.shape}", np.empty((0, 2))

        if not np.all(np.isfinite(arr)):
            return False, "Path contains NaN or Inf values", np.empty((0, 2))

        return True, "Path valid", arr[:, :2]

    def find_lookahead_point(
        self,
        vehicle_pos: Tuple[float, float],
        path_arr: np.ndarray,
        lookahead_dist: float,
    ) -> Tuple[Optional[Tuple[float, float]], int, float]:
        """
        Find target lookahead point along the path.

        Parameters
        ----------
        vehicle_pos : (x, y)
            Current vehicle 2D position.
        path_arr : np.ndarray, shape (N, 2)
            Path points in metric coordinates.
        lookahead_dist : float
            Lookahead distance L_d.

        Returns
        -------
        lookahead_point : Optional[Tuple[float, float]]
            Coordinates of target point, or None if none could be found.
        closest_idx : int
            Index of closest waypoint on path.
        dist_to_closest : float
            Distance from vehicle to closest waypoint.
        """
        vx, vy = vehicle_pos
        num_points = path_arr.shape[0]

        # 1. Find closest waypoint to vehicle
        diffs = path_arr - np.array([vx, vy])
        dists = np.hypot(diffs[:, 0], diffs[:, 1])
        closest_idx = int(np.argmin(dists))
        dist_to_closest = float(dists[closest_idx])

        # If vehicle is near or past the goal
        goal_point = (float(path_arr[-1, 0]), float(path_arr[-1, 1]))
        dist_to_goal = float(dists[-1])

        # 2. Search for circle-segment intersection along path starting at closest_idx
        # A circle of radius L_d around vehicle (vx, vy)
        best_point: Optional[Tuple[float, float]] = None

        for i in range(closest_idx, num_points - 1):
            p1 = path_arr[i]
            p2 = path_arr[i + 1]

            d = p2 - p1
            f = p1 - np.array([vx, vy])

            a = float(np.dot(d, d))
            b = float(2.0 * np.dot(f, d))
            c = float(np.dot(f, f) - lookahead_dist * lookahead_dist)

            if a < 1e-12:
                continue

            discriminant = b * b - 4.0 * a * c
            if discriminant >= 0.0:
                sqrt_disc = math.sqrt(discriminant)
                t1 = (-b - sqrt_disc) / (2.0 * a)
                t2 = (-b + sqrt_disc) / (2.0 * a)

                # We prefer the furthest valid intersection along the segment
                valid_ts = [t for t in (t1, t2) if -1e-5 <= t <= 1.0 + 1e-5]
                if valid_ts:
                    t_chosen = max(valid_ts)
                    t_chosen = max(0.0, min(1.0, t_chosen))
                    pt = p1 + t_chosen * d
                    best_point = (float(pt[0]), float(pt[1]))

        if best_point is not None:
            return best_point, closest_idx, dist_to_closest

        # 3. Fallback: if no segment intersection found
        # A. If remaining path is shorter than lookahead distance, target the goal
        if dist_to_goal <= lookahead_dist:
            return goal_point, closest_idx, dist_to_closest

        # B. If vehicle is before the path start (closest is 0 and vehicle is far from P0)
        # Search for first waypoint ahead that has distance >= lookahead_dist
        for i in range(closest_idx, num_points):
            if dists[i] >= lookahead_dist:
                return (float(path_arr[i, 0]), float(path_arr[i, 1])), closest_idx, dist_to_closest

        # C. Default fallback to goal or last point
        return goal_point, closest_idx, dist_to_closest

    def compute_command(
        self,
        vehicle_pose: Union[VehiclePose, Tuple[float, float, float], Any],
        path: Optional[Sequence[Tuple[float, float]]],
        lookahead_distance: Optional[float] = None,
        emergency_stop: bool = False,
    ) -> ControlCommand:
        """
        Compute Pure Pursuit control command for the vehicle.

        Parameters
        ----------
        vehicle_pose : VehiclePose or (x, y, yaw) or PoseEstimate
            Current estimated pose in metric world frame.
        path : Sequence[Tuple[float, float]]
            Planned 2D path in metric world coordinates.
        lookahead_distance : float, optional
            Override config lookahead distance if provided.
        emergency_stop : bool, default=False
            If True, immediately issue an emergency stop command.

        Returns
        -------
        ControlCommand
            Object containing linear_speed, angular_velocity, curvature,
            steering_angle, lookahead_point, goal_reached, and emergency_stop flag.
        """
        # 1. Caller explicit emergency stop
        if emergency_stop:
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=None,
                goal_reached=False,
                emergency_stop=True,
                message="Emergency stop explicitly commanded by caller.",
            )

        # 2. Parse vehicle pose
        try:
            pose = VehiclePose.from_any(vehicle_pose)
        except Exception as e:
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=None,
                goal_reached=False,
                emergency_stop=True,
                message=f"Invalid vehicle pose: {e}",
            )

        # 3. Validate path
        valid, msg, path_arr = self._validate_path(path)
        if not valid:
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=None,
                goal_reached=False,
                emergency_stop=True,
                message=f"Invalid path: {msg}",
            )

        # 4. Check goal reached condition
        goal = (float(path_arr[-1, 0]), float(path_arr[-1, 1]))
        dist_to_goal = math.hypot(goal[0] - pose.x, goal[1] - pose.y)

        if dist_to_goal <= self.config.goal_tolerance:
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=goal,
                goal_reached=True,
                emergency_stop=False,
                message=f"Goal reached (distance {dist_to_goal:.3f}m <= {self.config.goal_tolerance:.3f}m).",
            )

        # 5. Determine active lookahead distance
        ld = lookahead_distance if lookahead_distance is not None else self.config.lookahead_distance
        ld = max(self.config.min_lookahead_distance, min(ld, self.config.max_lookahead_distance))

        # 6. Find lookahead point
        lh_point, closest_idx, dist_to_path = self.find_lookahead_point(
            (pose.x, pose.y), path_arr, ld
        )

        if lh_point is None:
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=None,
                goal_reached=False,
                emergency_stop=True,
                message="No valid lookahead point found along path.",
            )

        # Check maximum allowed cross-track error (vehicle off-course safety check)
        if (
            self.config.max_allowed_crosstrack is not None
            and dist_to_path > self.config.max_allowed_crosstrack
        ):
            return ControlCommand(
                linear_speed=0.0,
                angular_velocity=0.0,
                steering_angle=0.0,
                curvature=0.0,
                lookahead_point=lh_point,
                goal_reached=False,
                emergency_stop=True,
                message=(
                    f"Vehicle cross-track distance {dist_to_path:.2f}m exceeds "
                    f"safety threshold {self.config.max_allowed_crosstrack:.2f}m."
                ),
            )

        # 7. Pure Pursuit Geometry
        dx = lh_point[0] - pose.x
        dy = lh_point[1] - pose.y
        actual_ld = math.hypot(dx, dy)

        if actual_ld < 1e-4:
            curvature = 0.0
            steering_angle = 0.0
        else:
            # Transform lookahead point to vehicle body frame:
            # x_local = dx * cos(yaw) + dy * sin(yaw) (forward)
            # y_local = -dx * sin(yaw) + dy * cos(yaw) (lateral)
            cos_yaw = math.cos(pose.yaw)
            sin_yaw = math.sin(pose.yaw)
            x_local = dx * cos_yaw + dy * sin_yaw
            y_local = -dx * sin_yaw + dy * cos_yaw

            # Heading error alpha:
            # alpha = atan2(y_local, x_local)
            # Pure pursuit curvature kappa = 2 * y_local / (L_d^2)
            curvature = 2.0 * y_local / (actual_ld * actual_ld)

            # Ackermann steering angle: delta = atan(curvature * wheelbase)
            steering_angle = math.atan(curvature * self.config.wheelbase)

        # 8. Speed Limiter:
        # A. Curvature slowdown: reduce speed when curvature is high
        # Formula: v_curve = v_max / (1 + gain * |kappa|)
        abs_kappa = abs(curvature)
        speed_factor = 1.0 / (1.0 + self.config.curvature_slowdown_gain * abs_kappa)
        target_speed = self.config.max_linear_speed * speed_factor

        # B. Goal proximity slowdown: ramp down when near goal
        if dist_to_goal < self.config.goal_slowdown_distance:
            goal_factor = dist_to_goal / max(self.config.goal_slowdown_distance, 1e-4)
            # Smooth deceleration ramp
            target_speed = target_speed * max(0.2, goal_factor)

        # Bound linear speed to [min_linear_speed, max_linear_speed]
        linear_speed = float(
            np.clip(target_speed, self.config.min_linear_speed, self.config.max_linear_speed)
        )

        # 9. Angular velocity command: omega = v * curvature
        omega = linear_speed * curvature
        # Limit angular velocity to configured safety bounds
        omega = float(np.clip(omega, -self.config.max_angular_speed, self.config.max_angular_speed))

        return ControlCommand(
            linear_speed=linear_speed,
            angular_velocity=omega,
            steering_angle=steering_angle,
            curvature=curvature,
            lookahead_point=lh_point,
            goal_reached=False,
            emergency_stop=False,
            message="Tracking path.",
        )
