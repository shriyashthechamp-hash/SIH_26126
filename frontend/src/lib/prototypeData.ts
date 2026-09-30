/**
 * DRISHTI Navigation System - Core Data Types & Adapter Contracts
 * Consistent with PROJECT_MASTERPLAN.md canonical architecture
 */

export type NavigabilityGroup =
  | 'SMOOTH'
  | 'ROUGH'
  | 'BUMPY'
  | 'FORBIDDEN'
  | 'OBSTACLE'
  | 'BACKGROUND';

export interface PerceptionClassMetric {
  name: NavigabilityGroup;
  percentage: number;
  costWeight: number | 'BLOCKED';
  color: string;
  description: string;
  isTraversable: boolean;
}

export interface PerceptionState {
  timestamp: number;
  frameId: number;
  model: 'SegFormer-B0' | 'Pretrained-Fallback';
  fps: number;
  inferenceMs: number;
  confidence: number;
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  classes: PerceptionClassMetric[];
  obstacleCount: number;
}

export interface LocalizationState {
  timestamp: number;
  pose: {
    x: number;
    y: number;
    yaw: number;
  };
  trackingQuality: number; // 0.0 to 1.0
  inliersCount: number;
  voState: 'TRACKING' | 'LOW_CONFIDENCE' | 'LOST';
  gpsStatus: 'DISABLED' | 'DISCONNECTED';
  linearVelocity: number; // m/s
  angularVelocity: number; // rad/s
}

export interface PathWaypoint {
  x: number;
  y: number;
  isObstacle?: boolean;
}

export interface NavigationState {
  timestamp: number;
  systemState: 'NAVIGATING' | 'PATH_INVALID' | 'REPLANNING' | 'SAFE_STOP' | 'GOAL_REACHED' | 'IDLE';
  planner: 'A* Cost-Aware' | 'A* Replanner';
  controller: 'Pure Pursuit';
  pathValid: boolean;
  pathLengthMeters: number;
  pathCost: number;
  minimumClearanceMeters: number;
  currentGoal: { x: number; y: number };
  activePath: PathWaypoint[];
  blockedCellsCount: number;
  replanLatencyMs: number;
  replanReason: string | null;
}

export interface CostmapState {
  width: number;
  height: number;
  resolution: number; // meters per cell
  origin: { x: number; y: number };
  grid: number[][]; // 2D matrix of costs (0 = free, 255 = blocked)
  obstacleRegions: { x: number; y: number; radius: number }[];
}

export interface MissionEvent {
  id: string;
  timestamp: string;
  code: string;
  message: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'CRITICAL';
  details?: Record<string, string | number>;
}

export interface DrishtiSystemState {
  isLiveBackend: boolean;
  mode: 'VISION_AUTONOMY' | 'MANUAL_TELEOP';
  perception: PerceptionState;
  localization: LocalizationState;
  navigation: NavigationState;
  costmap: CostmapState;
  recentEvents: MissionEvent[];
}

/**
 * Initial Mock Data for DRISHTI Simulator & Demo Mode
 */
export const INITIAL_CLASSES: PerceptionClassMetric[] = [
  { name: 'SMOOTH', percentage: 48.2, costWeight: 1.0, color: '#39FF88', description: 'Flat dirt path, gravel trail with minimal resistance', isTraversable: true },
  { name: 'ROUGH', percentage: 22.4, costWeight: 3.5, color: '#54D6FF', description: 'Uneven terrain, small pebbles, moderate rolling resistance', isTraversable: true },
  { name: 'BUMPY', percentage: 11.8, costWeight: 7.0, color: '#F5A623', description: 'Rocky soil, mounds, requires reduced traversal speed', isTraversable: true },
  { name: 'FORBIDDEN', percentage: 4.1, costWeight: 'BLOCKED', color: '#E056FD', description: 'Steep inclines, ditches, severe drop-offs', isTraversable: false },
  { name: 'OBSTACLE', percentage: 3.5, costWeight: 'BLOCKED', color: '#FF4D4D', description: 'Large boulders, tree trunks, artificial hazards', isTraversable: false },
  { name: 'BACKGROUND', percentage: 10.0, costWeight: 'BLOCKED', color: '#59605F', description: 'Sky, distant horizon, non-traversable boundary', isTraversable: false },
];

export const INITIAL_EVENTS: MissionEvent[] = [
  { id: 'evt-1', timestamp: '14:22:01.104', code: 'SYS_INIT', message: 'DRISHTI System booted in GPS-denied mode', severity: 'INFO' },
  { id: 'evt-2', timestamp: '14:22:01.320', code: 'PERC_ONLINE', message: 'SegFormer-B0 perception pipeline active (640x512)', severity: 'SUCCESS' },
  { id: 'evt-3', timestamp: '14:22:01.550', code: 'VO_LOCK', message: 'Visual odometry feature tracking initialized (240 inliers)', severity: 'SUCCESS' },
  { id: 'evt-4', timestamp: '14:22:02.100', code: 'MAP_GEN', message: 'Ground-plane BEV costmap constructed (20x20m @ 0.1m/px)', severity: 'INFO' },
  { id: 'evt-5', timestamp: '14:22:02.340', code: 'PATH_GEN', message: 'A* optimal route calculated to Goal [X: 12.0m, Y: 18.5m]', severity: 'SUCCESS' },
];

export const DEMO_SCRIPT_STEPS = [
  {
    step: 1,
    title: 'MISSION INITIALIZED',
    status: 'NAVIGATING' as const,
    pathValid: true,
    trackingQuality: 0.96,
    activeObstacle: false,
    replanReason: null,
    event: {
      id: 'demo-1',
      timestamp: '14:22:03.000',
      code: 'MISSION_START',
      message: 'Mission active. Pure pursuit tracking nominal waypoint trajectory.',
      severity: 'SUCCESS' as const,
    },
  },
  {
    step: 2,
    title: 'TERRAIN SCAN & TRACKING',
    status: 'NAVIGATING' as const,
    pathValid: true,
    trackingQuality: 0.94,
    activeObstacle: false,
    replanReason: null,
    event: {
      id: 'demo-2',
      timestamp: '14:22:04.200',
      code: 'TERRAIN_EVAL',
      message: 'Traversing smooth gravel segment. Clearance 1.42m.',
      severity: 'INFO' as const,
    },
  },
  {
    step: 3,
    title: 'DYNAMIC OBSTACLE DETECTED',
    status: 'PATH_INVALID' as const,
    pathValid: false,
    trackingQuality: 0.91,
    activeObstacle: true,
    blockedCount: 14,
    replanReason: '14 blocked cells detected along primary path trajectory',
    event: {
      id: 'demo-3',
      timestamp: '14:22:05.400',
      code: 'OBS_DETECTED',
      message: 'CRITICAL: Obstacle cluster encroaching planned corridor at +4.8m.',
      severity: 'WARNING' as const,
    },
  },
  {
    step: 4,
    title: 'CONFIDENCE GATING & SAFE STOP',
    status: 'SAFE_STOP' as const,
    pathValid: false,
    trackingQuality: 0.88,
    activeObstacle: true,
    blockedCount: 14,
    replanReason: 'Path invalidated. Rover deceleration triggered.',
    event: {
      id: 'demo-4',
      timestamp: '14:22:05.900',
      code: 'E_STOP_DECEL',
      message: 'Vehicle speed throttled to 0.0 m/s. Initiating costmap A* replan.',
      severity: 'CRITICAL' as const,
    },
  },
  {
    step: 5,
    title: 'A* COSTMAP REPLANNING',
    status: 'REPLANNING' as const,
    pathValid: false,
    trackingQuality: 0.92,
    activeObstacle: true,
    blockedCount: 14,
    replanReason: 'Searching cost-aware bypass via smooth left corridor...',
    event: {
      id: 'demo-5',
      timestamp: '14:22:06.350',
      code: 'REPLAN_EXEC',
      message: 'A* search evaluated 412 nodes. Cost delta +3.5m, clearance 0.9m.',
      severity: 'INFO' as const,
    },
  },
  {
    step: 6,
    title: 'SAFE ALTERNATIVE ROUTE LOCKED',
    status: 'NAVIGATING' as const,
    pathValid: true,
    trackingQuality: 0.95,
    activeObstacle: true,
    blockedCount: 0,
    replanReason: 'Alternative route accepted (+3.5m length, 0.9m clearance)',
    event: {
      id: 'demo-6',
      timestamp: '14:22:06.800',
      code: 'ROUTE_LOCKED',
      message: 'Bypass path generated. Controller resumed navigating to waypoint.',
      severity: 'SUCCESS' as const,
    },
  },
];
