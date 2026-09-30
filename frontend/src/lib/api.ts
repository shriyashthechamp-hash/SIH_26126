/**
 * DRISHTI Backend Adapter & WebSocket Bridge
 *
 * This module establishes the clean interface boundary for the frontend.
 * When FastAPI/WebSocket backend is enabled in future milestones,
 * this client connects to ws://localhost:8000/ws/telemetry without changing
 * any UI component logic.
 */

import { DrishtiSystemState, INITIAL_CLASSES, INITIAL_EVENTS } from './prototypeData';

export interface DrishtiAdapterConfig {
  backendUrl?: string;
  wsUrl?: string;
  useMockData: boolean;
}

export const DEFAULT_CONFIG: DrishtiAdapterConfig = {
  backendUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000/ws/telemetry',
  useMockData: true,
};

export class DrishtiTelemetryAdapter {
  private config: DrishtiAdapterConfig;
  private socket: WebSocket | null = null;
  private listeners: ((state: DrishtiSystemState) => void)[] = [];
  private currentState: DrishtiSystemState;

  constructor(config: Partial<DrishtiAdapterConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.currentState = this.createDefaultMockState();
  }

  public createDefaultMockState(): DrishtiSystemState {
    return {
      isLiveBackend: false,
      mode: 'VISION_AUTONOMY',
      perception: {
        timestamp: Date.now(),
        frameId: 1042,
        model: 'SegFormer-B0',
        fps: 22.4,
        inferenceMs: 44.6,
        confidence: 0.942,
        status: 'ONLINE',
        classes: INITIAL_CLASSES,
        obstacleCount: 1,
      },
      localization: {
        timestamp: Date.now(),
        pose: { x: 4.82, y: 7.15, yaw: 0.28 },
        trackingQuality: 0.94,
        inliersCount: 248,
        voState: 'TRACKING',
        gpsStatus: 'DISABLED',
        linearVelocity: 0.45,
        angularVelocity: 0.04,
      },
      navigation: {
        timestamp: Date.now(),
        systemState: 'NAVIGATING',
        planner: 'A* Cost-Aware',
        controller: 'Pure Pursuit',
        pathValid: true,
        pathLengthMeters: 14.8,
        pathCost: 32.4,
        minimumClearanceMeters: 1.25,
        currentGoal: { x: 12.0, y: 18.5 },
        activePath: [
          { x: 0, y: 0 },
          { x: 1.2, y: 2.1 },
          { x: 2.5, y: 4.5 },
          { x: 4.8, y: 7.2 },
          { x: 7.1, y: 10.8 },
          { x: 9.4, y: 14.5 },
          { x: 12.0, y: 18.5 },
        ],
        blockedCellsCount: 0,
        replanLatencyMs: 18.2,
        replanReason: null,
      },
      costmap: {
        width: 100,
        height: 100,
        resolution: 0.1,
        origin: { x: -5.0, y: 0 },
        grid: [],
        obstacleRegions: [{ x: 5.2, y: 9.1, radius: 0.8 }],
      },
      recentEvents: INITIAL_EVENTS,
    };
  }

  public getState(): DrishtiSystemState {
    return this.currentState;
  }

  public subscribe(callback: (state: DrishtiSystemState) => void): () => void {
    this.listeners.push(callback);
    callback(this.currentState);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  public notifyListeners() {
    for (const cb of this.listeners) {
      cb({ ...this.currentState });
    }
  }

  public updateLocalState(updater: (prev: DrishtiSystemState) => DrishtiSystemState) {
    this.currentState = updater(this.currentState);
    this.notifyListeners();
  }

  /**
   * Future Integration method for FastAPI / WebSocket server
   */
  public connectWebSocket(customUrl?: string) {
    if (this.config.useMockData) {
      console.info('[DRISHTI Adapter] Mock mode active — WebSocket live connection deferred to future backend integration');
      return;
    }

    const url = customUrl || this.config.wsUrl;
    try {
      this.socket = new WebSocket(url!);
      this.socket.onopen = () => {
        console.info(`[DRISHTI Adapter] Connected to live backend at ${url}`);
        this.currentState.isLiveBackend = true;
        this.notifyListeners();
      };
      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.currentState = { ...this.currentState, ...data, isLiveBackend: true };
          this.notifyListeners();
        } catch (err) {
          console.error('[DRISHTI Adapter] Error parsing telemetry message:', err);
        }
      };
      this.socket.onclose = () => {
        this.currentState.isLiveBackend = false;
        this.notifyListeners();
      };
    } catch (err) {
      console.warn('[DRISHTI Adapter] Live WebSocket connection failed. Operating in Simulation Mode.', err);
    }
  }

  public disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const telemetryAdapter = new DrishtiTelemetryAdapter();
