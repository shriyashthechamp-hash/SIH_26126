"""
Pydantic Schemas for DRISHTI FastAPI Backend.
Matches frontend contracts defined in frontend/src/lib/prototypeData.ts.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status: 'ok', 'degraded', or 'error'")
    service: str = "drishti-backend"
    mode: str = Field(..., description="'live' or 'demo_fallback'")
    device: str = Field(..., description="Compute device: CPU, CUDA, or MPS")
    model_loaded: bool = Field(..., description="True if SegFormer-B0 checkpoint is loaded")
    checkpoint_path: Optional[str] = None
    version: str = "1.0.0"


class PerceptionClassMetric(BaseModel):
    name: str
    percentage: float
    costWeight: Union[float, str]
    color: str
    description: str
    isTraversable: bool


class PerceptionData(BaseModel):
    timestamp: float
    frame_id: int
    model: str = "SegFormer-B0"
    fps: float
    inference_ms: float
    confidence: float
    status: str
    classes: List[PerceptionClassMetric]
    dominant_class: str
    obstacle_count: int


class CostmapData(BaseModel):
    width: int
    height: int
    resolution: float = 0.1
    mean_cost: float
    traversable_percent: float
    blocked_percent: float
    blocked_cells: int


class PathWaypoint(BaseModel):
    x: float
    y: float
    isObstacle: Optional[bool] = False


class NavigationData(BaseModel):
    system_state: str
    planner: str = "A* Cost-Aware"
    controller: str = "Pure Pursuit"
    path_valid: bool
    path_length_meters: float
    path_cost: float
    minimum_clearance_meters: float
    active_path: List[PathWaypoint]
    replan_latency_ms: float
    replan_reason: Optional[str] = None


class MissionEventSchema(BaseModel):
    id: str
    timestamp: str
    code: str
    message: str
    severity: str


class ProcessFrameResponse(BaseModel):
    success: bool
    timestamp: float
    perception: PerceptionData
    costmap: CostmapData
    navigation: NavigationData
    event: Optional[MissionEventSchema] = None
    overlays: Optional[Dict[str, str]] = None  # Base64 encoded JPEG preview images if requested
