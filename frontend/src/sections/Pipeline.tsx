import React, { useState } from 'react';
import { 
  Camera, 
  Layers, 
  Eye, 
  Grid, 
  Compass, 
  Navigation,
  ChevronRight,
  Info,
  CheckCircle2
} from 'lucide-react';

interface PipelineStep {
  id: string;
  stepNumber: string;
  title: string;
  subtitle: string;
  hardwareAlgorithm: string;
  icon: React.ReactNode;
  summary: string;
  technicalDetails: string[];
  metrics: { label: string; value: string }[];
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: 'perceive',
    stepNumber: '01',
    title: 'PERCEIVE',
    subtitle: 'Vision & Deep Segmentation',
    hardwareAlgorithm: 'Camera + SegFormer-B0',
    icon: <Camera className="w-5 h-5" />,
    summary: 'Captures raw 640x512 video frames and performs real-time pixel-level semantic classification across outdoor terrain.',
    technicalDetails: [
      'Pretrained transformer backbone fine-tuned on RUGD & RELLIS-3D datasets',
      'Classifies into 6 distinct navigation groups rather than raw semantic labels',
      'Weighted cross-entropy optimization for severe class imbalance handling'
    ],
    metrics: [
      { label: 'Input Target', value: '640x512' },
      { label: 'Inference', value: '22-30 FPS' },
      { label: 'Backbone', value: 'SegFormer-B0' }
    ]
  },
  {
    id: 'project',
    stepNumber: '02',
    title: 'PROJECT',
    subtitle: 'Ground-Plane BEV Transform',
    hardwareAlgorithm: 'Inverse Perspective Mapping (IPM)',
    icon: <Layers className="w-5 h-5" />,
    summary: 'Projects camera perspective segmentation onto an orthographic top-down Bird’s-Eye View (BEV) ground plane.',
    technicalDetails: [
      'Calibrated camera intrinsics matrix and pitch/height extrinsic geometry',
      'Radial and tangential lens distortion compensation',
      'Generates metric-scale top-down local spatial representation (0.1m/pixel)'
    ],
    metrics: [
      { label: 'Resolution', value: '0.1 m/cell' },
      { label: 'Field of View', value: '20m x 20m' },
      { label: 'Format', value: '2D Orthographic' }
    ]
  },
  {
    id: 'localize',
    stepNumber: '03',
    title: 'LOCALIZE',
    subtitle: 'Visual Odometry',
    hardwareAlgorithm: 'OpenCV Feature Tracking',
    icon: <Eye className="w-5 h-5" />,
    summary: 'Estimates continuous vehicle motion (X, Y, Yaw) frame-by-frame without GPS or satellite receivers.',
    technicalDetails: [
      'Feature detection and optical flow tracking across sequential frames',
      'Essential matrix decomposition with RANSAC outlier rejection',
      'Calculates real-time tracking confidence score and feature inlier counts'
    ],
    metrics: [
      { label: 'Degrees of Freedom', value: '6-DoF' },
      { label: 'GPS Dependency', value: '0% (Denied)' },
      { label: 'Pose Quality', value: '>92% Inliers' }
    ]
  },
  {
    id: 'map',
    stepNumber: '04',
    title: 'MAP',
    subtitle: 'Traversability Costmap',
    hardwareAlgorithm: 'Cost Function + Rolling Grid',
    icon: <Grid className="w-5 h-5" />,
    summary: 'Fuses BEV terrain projections and visual odometry pose into a spatial costmap representing terrain difficulty.',
    technicalDetails: [
      'Smooth terrain = low cost (1.0), Rough = medium (3.5), Bumpy = high (7.0)',
      'Obstacles and forbidden steep regions marked as impenetrable blocked cells',
      'Obstacle inflation radius applied to maintain vehicle clearance buffers'
    ],
    metrics: [
      { label: 'Cost Range', value: '1.0 to BLOCKED' },
      { label: 'Grid Size', value: '100x100 cells' },
      { label: 'Inflation Buffer', value: '0.6 m safety' }
    ]
  },
  {
    id: 'plan',
    stepNumber: '05',
    title: 'PLAN',
    subtitle: 'Cost-Aware A* Search',
    hardwareAlgorithm: 'Heuristic Graph Search',
    icon: <Compass className="w-5 h-5" />,
    summary: 'Searches the costmap to find the optimal minimum-cost trajectory from current pose to destination waypoint.',
    technicalDetails: [
      'Calculates energy-efficient path that prefers smooth trails over rough ground',
      'Continuous collision checking detects dynamic obstacles along active route',
      'Automatic dynamic replanning triggered within <20ms if path becomes blocked'
    ],
    metrics: [
      { label: 'Algorithm', value: 'Cost-Weighted A*' },
      { label: 'Replan Latency', value: '<20 ms' },
      { label: 'Success Rate', value: 'Closed-Loop Validated' }
    ]
  },
  {
    id: 'control',
    stepNumber: '06',
    title: 'CONTROL',
    subtitle: 'Pure Pursuit & Safety',
    hardwareAlgorithm: 'Kinematic Tracking + E-Stop',
    icon: <Navigation className="w-5 h-5" />,
    summary: 'Transforms planned geometric waypoint coordinates into motor throttle and steering commands for the UGV chassis.',
    technicalDetails: [
      'Lookahead-based steering calculation tracks path with smooth curvature',
      'Terrain-dependent speed limiter slows vehicle over bumpy or rough terrain',
      'Safety gate e-stop triggers immediate controlled stop if confidence drops'
    ],
    metrics: [
      { label: 'Controller', value: 'Pure Pursuit' },
      { label: 'Safety Mode', value: 'Confidence-Gated' },
      { label: 'Interface', value: 'Velocity v / w' }
    ]
  }
];

export const Pipeline: React.FC = () => {
  const [activeStepId, setActiveStepId] = useState<string>('perceive');
  const activeStep = PIPELINE_STEPS.find(s => s.id === activeStepId) || PIPELINE_STEPS[0];

  return (
    <section id="system" className="py-24 bg-[#080909] border-b border-[#252A29] relative overflow-hidden">
      <div className="absolute inset-0 bg-tech-grid opacity-30 pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>04 — SYSTEM PIPELINE</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
            THE CANONICAL ARCHITECTURE
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            An end-to-end, camera-first autonomy pipeline transforming raw photons into precise, obstacle-aware UGV motor actuation.
          </p>
        </div>

        {/* Pipeline Flow Stepper (Interactive 6 nodes) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
          {PIPELINE_STEPS.map((step, idx) => {
            const isSelected = step.id === activeStepId;
            return (
              <button
                key={step.id}
                onClick={() => setActiveStepId(step.id)}
                className={`relative p-4 rounded text-left transition-all border ${
                  isSelected
                    ? 'bg-[#151918] border-[#F5A623] shadow-lg shadow-[#F5A623]/5'
                    : 'bg-[#101313] border-[#252A29] hover:border-[#38403e] hover:bg-[#151918]'
                }`}
              >
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 z-20 text-[#59605F]">
                    <ChevronRight className="w-4 h-4" />
                  </div>
                )}

                <div className="flex items-center justify-between mb-3 font-mono-tech">
                  <span className={`text-xs font-bold ${isSelected ? 'text-[#F5A623]' : 'text-[#59605F]'}`}>
                    {step.stepNumber}
                  </span>
                  <div className={`p-1.5 rounded ${isSelected ? 'text-[#F5A623] bg-[#F5A623]/10' : 'text-[#8E9594]'}`}>
                    {step.icon}
                  </div>
                </div>

                <div className="font-heading font-bold text-sm text-[#F1F0EA]">
                  {step.title}
                </div>

                <div className="font-mono-tech text-[10px] text-[#8E9594] truncate mt-0.5">
                  {step.subtitle}
                </div>

                {isSelected && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#F5A623]" />
                )}
              </button>
            );
          })}
        </div>

        {/* Selected Step Detail Panel */}
        <div className="bg-[#101313] border border-[#252A29] rounded-lg p-6 sm:p-8 corner-brackets">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            <div className="lg:col-span-7 space-y-6">
              
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono-tech text-xs px-2.5 py-1 bg-[#151918] border border-[#252A29] text-[#F5A623] rounded">
                  STAGE {activeStep.stepNumber} OF 06
                </span>
                <span className="font-mono-tech text-xs text-[#8E9594]">
                  ENGINE: <span className="text-[#F1F0EA] font-semibold">{activeStep.hardwareAlgorithm}</span>
                </span>
              </div>

              <div>
                <h3 className="font-heading font-extrabold text-2xl sm:text-3xl text-[#F1F0EA]">
                  {activeStep.title} — {activeStep.subtitle}
                </h3>
                <p className="mt-3 text-base text-[#8E9594] leading-relaxed">
                  {activeStep.summary}
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <div className="font-mono-tech text-xs text-[#59605F] uppercase tracking-wider">
                  Implementation Highlights:
                </div>
                {activeStep.technicalDetails.map((detail, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-sm text-[#F1F0EA]/90 font-mono-tech">
                    <CheckCircle2 className="w-4 h-4 text-[#39FF88] shrink-0 mt-0.5" />
                    <span>{detail}</span>
                  </div>
                ))}
              </div>

            </div>

            <div className="lg:col-span-5 bg-[#151918] border border-[#252A29] rounded p-5 font-mono-tech space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-[#252A29] text-xs">
                <span className="text-[#8E9594] flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-[#54D6FF]" /> SPECIFICATION METRICS
                </span>
                <span className="text-[#39FF88] text-[10px]">VERIFIED IN CODE</span>
              </div>

              <div className="space-y-4">
                {activeStep.metrics.map((metric, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-[#1c2221]">
                    <span className="text-[#8E9594]">{metric.label}</span>
                    <span className="text-[#F1F0EA] font-bold">{metric.value}</span>
                  </div>
                ))}
              </div>

              <div className="pt-2 text-[11px] text-[#59605F] leading-normal">
                Canonical flow step {activeStep.stepNumber}. Data is streamed sequentially with timestamp synchronization across perception and planning threads.
              </div>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
};
