import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  RotateCcw, 
  FastForward, 
  Radio, 
  Eye, 
  Crosshair, 
  Compass, 
  ArrowLeft,
  Layers,
  Info
} from 'lucide-react';
import { 
  DrishtiSystemState, 
  DEMO_SCRIPT_STEPS, 
  INITIAL_CLASSES, 
  MissionEvent 
} from '../lib/prototypeData';
import { telemetryAdapter } from '../lib/api';

interface PrototypePageProps {
  onBackToHome: () => void;
}

export const PrototypePage: React.FC<PrototypePageProps> = ({ onBackToHome }) => {
  const [systemState, setSystemState] = useState<DrishtiSystemState>(() => telemetryAdapter.getState());
  const [demoStepIndex, setDemoStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [activeObstacle, setActiveObstacle] = useState<boolean>(false);
  const [showSegOverlay, setShowSegOverlay] = useState<boolean>(true);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const playTimerRef = useRef<number | null>(null);

  // Clock simulation
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Demo auto-player loop
  useEffect(() => {
    if (isPlaying) {
      playTimerRef.current = window.setTimeout(() => {
        if (demoStepIndex < DEMO_SCRIPT_STEPS.length - 1) {
          applyDemoStep(demoStepIndex + 1);
        } else {
          setIsPlaying(false);
        }
      }, 2500);
    }
    return () => {
      if (playTimerRef.current) {
        clearTimeout(playTimerRef.current);
      }
    };
  }, [isPlaying, demoStepIndex]);

  const applyDemoStep = (stepIdx: number) => {
    setDemoStepIndex(stepIdx);
    const stepData = DEMO_SCRIPT_STEPS[stepIdx];
    if (!stepData) return;

    setActiveObstacle(stepData.activeObstacle);

    setSystemState((prev) => {
      const isReplan = stepData.step >= 5;
      const isBlocked = stepData.status === 'PATH_INVALID' || stepData.status === 'SAFE_STOP';

      const updatedPath = isReplan
        ? [
            { x: 0, y: 0 },
            { x: 1.2, y: 2.5 },
            { x: 2.1, y: 5.5 }, // Bypassing left
            { x: 3.8, y: 8.8 },
            { x: 7.5, y: 12.5 },
            { x: 10.2, y: 15.8 },
            { x: 12.0, y: 18.5 },
          ]
        : [
            { x: 0, y: 0 },
            { x: 1.2, y: 2.1 },
            { x: 2.5, y: 4.5 }, // Pierces nominal corridor
            { x: 4.8, y: 7.2 },
            { x: 7.1, y: 10.8 },
            { x: 9.4, y: 14.5 },
            { x: 12.0, y: 18.5 },
          ];

      const newEvent: MissionEvent = {
        ...stepData.event,
        id: `evt-${Date.now()}`,
      };

      return {
        ...prev,
        localization: {
          ...prev.localization,
          trackingQuality: stepData.trackingQuality,
          linearVelocity: stepData.status === 'SAFE_STOP' ? 0.0 : isBlocked ? 0.15 : 0.45,
        },
        navigation: {
          ...prev.navigation,
          systemState: stepData.status,
          pathValid: stepData.pathValid,
          activePath: updatedPath,
          blockedCellsCount: stepData.blockedCount || 0,
          replanReason: stepData.replanReason,
          pathLengthMeters: isReplan ? 18.3 : 14.8,
          minimumClearanceMeters: isReplan ? 0.9 : isBlocked ? 0.15 : 1.25,
        },
        recentEvents: [newEvent, ...prev.recentEvents.slice(0, 9)],
      };
    });
  };

  const handleStartDemo = () => {
    applyDemoStep(0);
    setIsPlaying(true);
  };

  const handleNextStep = () => {
    if (demoStepIndex < DEMO_SCRIPT_STEPS.length - 1) {
      applyDemoStep(demoStepIndex + 1);
    } else {
      applyDemoStep(0);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    if (playTimerRef.current) clearTimeout(playTimerRef.current);
    applyDemoStep(0);
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `T+00:${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const currentStep = DEMO_SCRIPT_STEPS[demoStepIndex];

  return (
    <div className="min-h-screen bg-[#080909] text-[#F1F0EA] flex flex-col font-sans">
      
      {/* ============================================================ */}
      {/* 1. TOP TELEMETRY BAR                                         */}
      {/* ============================================================ */}
      <header className="bg-[#101313] border-b border-[#252A29] px-4 py-3 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 font-mono-tech text-xs">
          
          {/* Left: Brand & Mode */}
          <div className="flex items-center gap-4">
            <button
              onClick={onBackToHome}
              className="flex items-center gap-1.5 text-[#8E9594] hover:text-[#F5A623] transition-colors pr-3 border-r border-[#252A29]"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">OVERVIEW</span>
            </button>

            <div className="flex items-center gap-2">
              <span className="font-heading font-extrabold text-[#F1F0EA] tracking-wider text-sm">
                DRISHTI
              </span>
              <span className="text-[#59605F]">//</span>
              <span className="text-[#F5A623] font-bold">MISSION CONTROL</span>
            </div>
          </div>

          {/* Center: System Status Telemetry */}
          <div className="flex items-center gap-4 flex-wrap text-[11px]">
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-[#151918] border border-[#252A29] rounded">
              <span className="w-2 h-2 rounded-full bg-[#39FF88] pulse-dot" />
              <span className="text-[#8E9594]">SYSTEM:</span>
              <span className="text-[#39FF88] font-bold">ONLINE</span>
            </div>

            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-[#151918] border border-[#FF4D4D]/30 rounded">
              <Radio className="w-3 h-3 text-[#FF4D4D]" />
              <span className="text-[#8E9594]">GPS:</span>
              <span className="text-[#FF4D4D] font-bold">DISABLED</span>
            </div>

            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-[#151918] border border-[#54D6FF]/30 rounded">
              <Eye className="w-3 h-3 text-[#54D6FF]" />
              <span className="text-[#8E9594]">MODE:</span>
              <span className="text-[#54D6FF] font-bold">VISION AUTONOMY</span>
            </div>

            <div className="hidden md:flex items-center gap-1.5 text-[#8E9594]">
              <span>CLOCK:</span>
              <span className="text-[#F1F0EA]">{formatTime(elapsedSeconds)}</span>
            </div>
          </div>

          {/* Right: Simulation Controller */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#F5A623] px-2 py-0.5 bg-[#F5A623]/10 border border-[#F5A623]/30 rounded">
              SIMULATED DEMO
            </span>
          </div>

        </div>
      </header>

      {/* ============================================================ */}
      {/* 2. DEMO INTERFACE DISCLAIMER BANNER                          */}
      {/* ============================================================ */}
      <div className="bg-[#151918] border-b border-[#252A29] px-4 py-2 font-mono-tech text-[11px] text-[#8E9594] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-[#54D6FF]" />
          <span>
            <strong className="text-[#F1F0EA]">DEMO INTERFACE:</strong> LIVE PERCEPTION BACKEND — NOT CONNECTED. (Full adapter contracts ready for FastAPI/WebSocket bridge).
          </span>
        </div>
        <div className="text-[#59605F]">
          MASTERPLAN COMPLIANT (§22–24)
        </div>
      </div>

      {/* ============================================================ */}
      {/* 3. MAIN DASHBOARD CONTENT GRID                               */}
      {/* ============================================================ */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        
        {/* Step Banner & Interactive Controller */}
        <div className="bg-[#101313] border border-[#252A29] rounded-lg p-4 corner-brackets flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 font-mono-tech text-xs">
              <span className="text-[#F5A623] font-bold">DEMO SCENARIO STEP {demoStepIndex + 1}/6:</span>
              <span className="text-[#F1F0EA] font-semibold">{currentStep.title}</span>
            </div>
            <div className="font-mono-tech text-[11px] text-[#8E9594]">
              {currentStep.event.message}
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono-tech text-xs">
            <button
              onClick={handleStartDemo}
              disabled={isPlaying}
              className="btn-primary py-2 px-3 text-xs flex items-center gap-1.5 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{isPlaying ? 'PLAYING...' : 'START DEMO'}</span>
            </button>

            <button
              onClick={handleNextStep}
              className="btn-secondary py-2 px-3 text-xs flex items-center gap-1.5"
            >
              <FastForward className="w-3.5 h-3.5" />
              <span>STEP</span>
            </button>

            <button
              onClick={handleReset}
              className="btn-secondary py-2 px-3 text-xs flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>RESET</span>
            </button>
          </div>
        </div>

        {/* ============================================================ */}
        {/* 4. DUAL VIEW: CAMERA FEED vs 2D BEV LOCAL MAP               */}
        {/* ============================================================ */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT: CAMERA SENSOR FEED */}
          <div className="lg:col-span-6 bg-[#101313] border border-[#252A29] rounded-lg p-4 corner-brackets flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#252A29] font-mono-tech text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#39FF88]" />
                  <span className="font-bold text-[#F1F0EA]">FORWARD STEREO CAM</span>
                </div>
                <div className="flex items-center gap-3 text-[#8E9594]">
                  <span>22.4 FPS</span>
                  <button
                    onClick={() => setShowSegOverlay(!showSegOverlay)}
                    className="hover:text-[#F5A623] flex items-center gap-1 text-[10px] uppercase underline cursor-pointer"
                  >
                    <Layers className="w-3 h-3" />
                    <span>{showSegOverlay ? 'HIDE MASK' : 'SHOW MASK'}</span>
                  </button>
                </div>
              </div>

              {/* Camera Video / Image Container with Reticle */}
              <div className="relative aspect-[16/10] bg-[#080909] rounded border border-[#252A29] overflow-hidden">
                <img
                  src="/assets/prototype/camera_feed.jpg"
                  alt="DRISHTI Rover Forward Camera Perception Feed"
                  className="w-full h-full object-cover"
                />

                <div className="scanlines absolute inset-0 pointer-events-none" />

                {/* Optional Segmentation Overlay */}
                {showSegOverlay && (
                  <div className="absolute inset-0 pointer-events-none">
                    <svg className="w-full h-full" viewBox="0 0 640 400" preserveAspectRatio="none">
                      {/* Smooth Trail Polygon */}
                      <polygon 
                        points="140,400 500,400 350,180 290,180" 
                        fill="rgba(57, 255, 136, 0.25)" 
                        stroke="#39FF88" 
                        strokeWidth="1"
                      />

                      {/* Rough Flanks */}
                      <polygon 
                        points="0,400 140,400 290,180 0,180" 
                        fill="rgba(84, 214, 255, 0.2)" 
                      />
                      <polygon 
                        points="500,400 640,400 640,180 350,180" 
                        fill="rgba(245, 166, 35, 0.2)" 
                      />

                      {/* Dynamic Obstacle Box when active */}
                      {activeObstacle && (
                        <g>
                          <rect 
                            x="295" 
                            y="230" 
                            width="60" 
                            height="45" 
                            fill="rgba(255, 77, 77, 0.7)" 
                            stroke="#FF4D4D" 
                            strokeWidth="2" 
                          />
                          <text 
                            x="300" 
                            y="222" 
                            fill="#FF4D4D" 
                            fontSize="11" 
                            fontFamily="monospace" 
                            fontWeight="bold"
                          >
                            HAZARD [+4.8m]
                          </text>
                        </g>
                      )}
                    </svg>
                  </div>
                )}

                {/* HUD Overlay Reticle */}
                <div className="absolute inset-0 p-3 flex flex-col justify-between pointer-events-none font-mono-tech text-[10px]">
                  <div className="flex justify-between items-center text-[#54D6FF] bg-[#080909]/70 px-2 py-0.5 rounded border border-[#252A29]">
                    <span>EXP: AUTO (ISO 100)</span>
                    <span>FOV: 85° H-FOV</span>
                  </div>

                  {/* Dynamic Alert Banner over Camera */}
                  {activeObstacle && (
                    <div className="self-center bg-[#FF4D4D]/90 text-[#080909] font-bold px-3 py-1 rounded text-xs animate-pulse">
                      OBSTACLE ENCROACHMENT DETECTED
                    </div>
                  )}

                  <div className="flex justify-between text-[#8E9594] bg-[#080909]/80 px-2 py-1 rounded border border-[#252A29]">
                    <span>CONFIDENCE: {(systemState.perception.confidence * 100).toFixed(1)}%</span>
                    <span className="text-[#39FF88]">MODEL: SegFormer-B0</span>
                  </div>
                </div>

                {/* Sweep animation line */}
                <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#54D6FF]/70 to-transparent reticle-sweep pointer-events-none" />
              </div>
            </div>

            <div className="mt-3 font-mono-tech text-[11px] text-[#59605F] flex justify-between">
              <span>CAMERA ID: DEV_CAM_01</span>
              <span>INFERENCE: 44.6ms</span>
            </div>
          </div>

          {/* RIGHT: 2D BEV LOCAL MAP & A* TRAJECTORY */}
          <div className="lg:col-span-6 bg-[#101313] border border-[#252A29] rounded-lg p-4 corner-brackets flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#252A29] font-mono-tech text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#54D6FF]" />
                  <span className="font-bold text-[#F1F0EA]">BEV LOCAL COSTMAP</span>
                </div>
                <div className="text-[#8E9594] text-[11px]">
                  20m x 20m [0.1m/CELL]
                </div>
              </div>

              {/* BEV Map Canvas Screen */}
              <div className="relative aspect-[16/10] bg-[#080909] rounded border border-[#252A29] overflow-hidden bg-tech-grid-dense flex items-center justify-center p-2">
                
                <svg className="w-full h-full" viewBox="0 0 400 250">
                  {/* Grid Axis Coordinate Lines */}
                  <line x1="200" y1="0" x2="200" y2="250" stroke="#1c2221" strokeWidth="1" strokeDasharray="4 4" />
                  <line x1="0" y1="125" x2="400" y2="125" stroke="#1c2221" strokeWidth="1" strokeDasharray="4 4" />

                  {/* Traversable Corridor Polygon */}
                  <polygon 
                    points="140,240 260,240 240,40 160,40" 
                    fill="rgba(57, 255, 136, 0.08)" 
                    stroke="#252A29" 
                    strokeWidth="1" 
                  />

                  {/* Dynamic Obstacle on BEV */}
                  {activeObstacle && (
                    <g>
                      <circle cx="200" cy="140" r="28" fill="rgba(255, 77, 77, 0.15)" stroke="#FF4D4D" strokeWidth="1" strokeDasharray="2 2" />
                      <circle cx="200" cy="140" r="16" fill="#FF4D4D" stroke="#FF4D4D" strokeWidth="2" />
                      <text x="218" y="144" fill="#FF4D4D" fontSize="10" fontFamily="monospace" fontWeight="bold">BLOCKED</text>
                    </g>
                  )}

                  {/* Planned Trajectory Path */}
                  {systemState.navigation.systemState === 'PATH_INVALID' || systemState.navigation.systemState === 'SAFE_STOP' ? (
                    <path
                      d="M 200 230 L 200 50"
                      fill="none"
                      stroke="#FF4D4D"
                      strokeWidth="3"
                      strokeDasharray="4 4"
                    />
                  ) : systemState.navigation.systemState === 'REPLANNING' ? (
                    <g>
                      <path
                        d="M 200 230 Q 140 140 190 50"
                        fill="none"
                        stroke="#F5A623"
                        strokeWidth="2"
                        strokeDasharray="3 3"
                        className="animate-pulse"
                      />
                      <path
                        d="M 200 230 Q 260 140 210 50"
                        fill="none"
                        stroke="#F5A623"
                        strokeWidth="1"
                        strokeDasharray="2 2"
                        opacity="0.5"
                      />
                    </g>
                  ) : activeObstacle ? (
                    <path
                      d="M 200 230 Q 155 140 195 50"
                      fill="none"
                      stroke="#39FF88"
                      strokeWidth="3.5"
                    />
                  ) : (
                    <path
                      d="M 200 230 L 200 50"
                      fill="none"
                      stroke="#39FF88"
                      strokeWidth="3"
                    />
                  )}

                  {/* Start / Rover Pose Marker */}
                  <g transform="translate(200, 230)">
                    <circle cx="0" cy="0" r="9" fill="#54D6FF" stroke="#F1F0EA" strokeWidth="2" />
                    <polygon points="0,-7 5,5 -5,5" fill="#080909" />
                    <text x="14" y="4" fill="#54D6FF" fontSize="11" fontFamily="monospace" fontWeight="bold">ROVER (0,0)</text>
                  </g>

                  {/* Goal Marker */}
                  <g transform="translate(195, 50)">
                    <circle cx="0" cy="0" r="8" fill="#F5A623" stroke="#F1F0EA" strokeWidth="2" />
                    <text x="14" y="4" fill="#F5A623" fontSize="11" fontFamily="monospace" fontWeight="bold">GOAL WP (12, 18.5)</text>
                  </g>
                </svg>

                {/* Map Bottom Status */}
                <div className="absolute bottom-2 left-2 right-2 flex justify-between font-mono-tech text-[10px] text-[#8E9594] bg-[#080909]/80 px-2 py-1 rounded border border-[#252A29]">
                  <span>PLANNER: A* COST-WEIGHTED</span>
                  <span>
                    PATH STATUS:{' '}
                    <strong className={systemState.navigation.pathValid ? 'text-[#39FF88]' : 'text-[#FF4D4D]'}>
                      {systemState.navigation.pathValid ? 'VALID' : 'INVALIDATED'}
                    </strong>
                  </span>
                </div>

              </div>
            </div>

            <div className="mt-3 font-mono-tech text-[11px] text-[#59605F] flex justify-between">
              <span>CLEARANCE: {systemState.navigation.minimumClearanceMeters}m</span>
              <span>PATH COST: {systemState.navigation.pathCost.toFixed(1)}</span>
            </div>
          </div>

        </div>

        {/* ============================================================ */}
        {/* 5. TELEMETRY CARDS: PERCEPTION, LOCALIZATION, NAVIGATION     */}
        {/* ============================================================ */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* CARD 1: PERCEPTION PANEL */}
          <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#252A29] font-mono-tech text-xs">
              <span className="font-bold text-[#F1F0EA] flex items-center gap-1.5">
                <Eye className="w-4 h-4 text-[#39FF88]" /> PERCEPTION (6 CLASSES)
              </span>
              <span className="text-[10px] text-[#F5A623] px-1.5 py-0.2 bg-[#F5A623]/10 border border-[#F5A623]/30 rounded">
                DEMO DATA
              </span>
            </div>

            {/* Class distribution bars */}
            <div className="space-y-2.5 font-mono-tech text-xs">
              {INITIAL_CLASSES.map((cls) => (
                <div key={cls.name} className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#8E9594]">{cls.name}</span>
                    <span className="text-[#F1F0EA]">{cls.percentage}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#151918] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${cls.percentage}%`,
                        backgroundColor: cls.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 text-[10px] font-mono-tech text-[#59605F] border-t border-[#1c2221]">
              Inference Resolution: 640x512 @ 22.4 FPS
            </div>
          </div>

          {/* CARD 2: LOCALIZATION PANEL */}
          <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#252A29] font-mono-tech text-xs">
              <span className="font-bold text-[#F1F0EA] flex items-center gap-1.5">
                <Crosshair className="w-4 h-4 text-[#54D6FF]" /> LOCALIZATION (VO)
              </span>
              <span className="text-[10px] text-[#54D6FF] px-1.5 py-0.2 bg-[#54D6FF]/10 border border-[#54D6FF]/30 rounded">
                SIMULATED
              </span>
            </div>

            <div className="space-y-3 font-mono-tech text-xs">
              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">COORDINATE X:</span>
                <span className="text-[#F1F0EA] font-bold">+{systemState.localization.pose.x.toFixed(2)} m</span>
              </div>
              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">COORDINATE Y:</span>
                <span className="text-[#F1F0EA] font-bold">+{systemState.localization.pose.y.toFixed(2)} m</span>
              </div>
              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">HEADING YAW:</span>
                <span className="text-[#54D6FF] font-bold">{systemState.localization.pose.yaw.toFixed(2)} rad</span>
              </div>
              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">TRACKING QUALITY:</span>
                <span className="text-[#39FF88] font-bold">{(systemState.localization.trackingQuality * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="pt-2 text-[10px] font-mono-tech text-[#59605F] border-t border-[#1c2221]">
              Inliers: 248 features // No satellite fix
            </div>
          </div>

          {/* CARD 3: NAVIGATION & REPLAN PANEL */}
          <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#252A29] font-mono-tech text-xs">
              <span className="font-bold text-[#F1F0EA] flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-[#F5A623]" /> NAVIGATION & REPLAN
              </span>
              <span className="text-[10px] text-[#39FF88] px-1.5 py-0.2 bg-[#39FF88]/10 border border-[#39FF88]/30 rounded">
                DEMO STATE
              </span>
            </div>

            <div className="space-y-3 font-mono-tech text-xs">
              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between items-center">
                <span className="text-[#8E9594]">SYSTEM STATE:</span>
                <span className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                  systemState.navigation.systemState === 'NAVIGATING'
                    ? 'text-[#39FF88] bg-[#39FF88]/10 border border-[#39FF88]/30'
                    : systemState.navigation.systemState === 'REPLANNING'
                    ? 'text-[#F5A623] bg-[#F5A623]/10 border border-[#F5A623]/30'
                    : 'text-[#FF4D4D] bg-[#FF4D4D]/10 border border-[#FF4D4D]/30'
                }`}>
                  {systemState.navigation.systemState}
                </span>
              </div>

              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">PLANNER ENGINE:</span>
                <span className="text-[#F1F0EA]">{systemState.navigation.planner}</span>
              </div>

              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">CONTROLLER:</span>
                <span className="text-[#F1F0EA]">{systemState.navigation.controller}</span>
              </div>

              <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex justify-between">
                <span className="text-[#8E9594]">REPLAN LATENCY:</span>
                <span className="text-[#39FF88] font-bold">{systemState.navigation.replanLatencyMs} ms</span>
              </div>
            </div>

            <div className="pt-2 text-[10px] font-mono-tech text-[#59605F] border-t border-[#1c2221]">
              Reason: {systemState.navigation.replanReason || 'Nominal waypoint tracking'}
            </div>
          </div>

        </div>

        {/* ============================================================ */}
        {/* 6. EVENT TIMELINE STREAM                                     */}
        {/* ============================================================ */}
        <div className="bg-[#101313] border border-[#252A29] rounded-lg p-5 corner-brackets space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#252A29] font-mono-tech text-xs">
            <span className="font-bold text-[#F1F0EA] flex items-center gap-2">
              <Compass className="w-4 h-4 text-[#F5A623]" />
              <span>REAL-TIME MISSION EVENT LOG STREAM</span>
            </span>
            <span className="text-[#59605F] text-[11px]">
              CANONICAL AUDIT LOGS
            </span>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto pr-1 font-mono-tech text-xs">
            {systemState.recentEvents.map((evt) => {
              let badgeColor = 'text-[#54D6FF] border-[#54D6FF]/30 bg-[#54D6FF]/10';
              if (evt.severity === 'SUCCESS') badgeColor = 'text-[#39FF88] border-[#39FF88]/30 bg-[#39FF88]/10';
              if (evt.severity === 'WARNING') badgeColor = 'text-[#F5A623] border-[#F5A623]/30 bg-[#F5A623]/10';
              if (evt.severity === 'CRITICAL') badgeColor = 'text-[#FF4D4D] border-[#FF4D4D]/30 bg-[#FF4D4D]/10';

              return (
                <div
                  key={evt.id}
                  className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:border-[#38403e] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[#59605F] text-[10px] shrink-0">
                      [{evt.timestamp}]
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded border font-bold shrink-0 ${badgeColor}`}>
                      {evt.code}
                    </span>
                    <span className="text-[#F1F0EA] text-[11px]">
                      {evt.message}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#59605F] uppercase shrink-0">
                    SEV: {evt.severity}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

      </main>

    </div>
  );
};
