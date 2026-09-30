/**
 * DRISHTI Backend Adapter & WebSocket Bridge
 *
 * Connects the React frontend to the FastAPI/WebSocket backend.
 * Uses Vite environment variables with graceful fallback to local and mock modes.
 */

import { DrishtiSystemState, INITIAL_CLASSES, INITIAL_EVENTS } from './prototypeData';

export interface DrishtiAdapterConfig {
  backendUrl: string;
  wsUrl: string;
  useMockData: boolean;
}

// Read from environment variables if defined, otherwise fallback to local backend
const ENV_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ENV_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/telemetry';

export const DEFAULT_CONFIG: DrishtiAdapterConfig = {
  backendUrl: ENV_API_URL,
  wsUrl: ENV_WS_URL,
  useMockData: false,
};

export class DrishtiTelemetryAdapter {
  private config: DrishtiAdapterConfig;
  private socket: WebSocket | null = null;
  private listeners: ((state: DrishtiSystemState) => void)[] = [];
  private currentState: DrishtiSystemState;
  private isConnecting: boolean = false;
  private pingInterval: number | null = null;

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

  public getBackendUrl(): string {
    return this.config.backendUrl;
  }

  public getWsUrl(): string {
    return this.config.wsUrl;
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
   * Health Check to verify backend status
   */
  public async checkHealth(): Promise<{ ok: boolean; data?: any; error?: string }> {
    try {
      const response = await fetch(`${this.config.backendUrl}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        return { ok: false, error: `HTTP ${response.status}` };
      }
      const data = await response.json();
      return { ok: true, data };
    } catch (err: any) {
      return { ok: false, error: err?.message || 'Network request failed' };
    }
  }

  /**
   * Send a captured video frame to the backend via POST /api/process-frame
   */
  public async sendFrame(blob: Blob): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      const formData = new FormData();
      formData.append('frame', blob, 'frame.jpg');

      const response = await fetch(`${this.config.backendUrl}/api/process-frame`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        return { success: false, error: `HTTP ${response.status}` };
      }

      const data = await response.json();
      
      // Update internal telemetry state with live perception output
      if (data && data.perception) {
        this.updateLocalState((prev) => ({
          ...prev,
          isLiveBackend: true,
          perception: {
            ...prev.perception,
            ...data.perception,
            status: 'ONLINE',
          },
          costmap: {
            ...prev.costmap,
            ...data.costmap,
          },
          navigation: {
            ...prev.navigation,
            ...data.navigation,
            activePath: data.navigation.active_path || prev.navigation.activePath,
            pathValid: data.navigation.path_valid ?? prev.navigation.pathValid,
            systemState: data.navigation.system_state || prev.navigation.systemState,
          },
          recentEvents: data.event ? [data.event, ...prev.recentEvents.slice(0, 9)] : prev.recentEvents,
        }));
      }

      return { success: true, data };
    } catch (err: any) {
      return { success: false, error: err?.message || 'Frame upload failed' };
    }
  }

  /**
   * WebSocket telemetry connection with auto-ping
   */
  public connectWebSocket(onStateUpdate?: (state: DrishtiSystemState) => void) {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const url = this.config.wsUrl;
    try {
      this.isConnecting = true;
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        this.isConnecting = false;
        console.info(`[DRISHTI Adapter] Connected to WebSocket at ${url}`);
        this.currentState.isLiveBackend = true;
        this.notifyListeners();

        // Setup keepalive ping every 10s
        this.pingInterval = window.setInterval(() => {
          if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send('PING');
          }
        }, 10000);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.perception) {
            this.updateLocalState((prev) => ({
              ...prev,
              isLiveBackend: true,
              perception: { ...prev.perception, ...data.perception },
              costmap: { ...prev.costmap, ...data.costmap },
              navigation: {
                ...prev.navigation,
                ...data.navigation,
                activePath: data.navigation.active_path || prev.navigation.activePath,
                pathValid: data.navigation.path_valid ?? prev.navigation.pathValid,
                systemState: data.navigation.system_state || prev.navigation.systemState,
              },
              recentEvents: data.event ? [data.event, ...prev.recentEvents.slice(0, 9)] : prev.recentEvents,
            }));
            if (onStateUpdate) onStateUpdate(this.currentState);
          }
        } catch (err) {
          // Non-JSON message (e.g., PONG)
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.currentState.isLiveBackend = false;
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.notifyListeners();
      };

      this.socket.onerror = () => {
        this.isConnecting = false;
        this.currentState.isLiveBackend = false;
        this.notifyListeners();
      };
    } catch (err) {
      this.isConnecting = false;
      this.currentState.isLiveBackend = false;
      this.notifyListeners();
    }
  }

  public disconnect() {
    if (this.pingInterval) clearInterval(this.pingInterval);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const telemetryAdapter = new DrishtiTelemetryAdapter();
