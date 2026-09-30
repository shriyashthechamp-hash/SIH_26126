import React, { useState } from 'react';
import { Layers, Grid, Compass, Eye } from 'lucide-react';

export const CostmapVisualizer: React.FC = () => {
  const [activeView, setActiveView] = useState<'camera' | 'segmentation' | 'costmap' | 'path'>('path');

  return (
    <section id="costmap" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
              <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
              <span>06 — VISUAL COSTMAP CONVERSION</span>
            </div>
            <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
              FROM PIXELS TO TRAVERSABLE PATHS
            </h2>
            <p className="mt-4 text-base text-[#8E9594]">
              Simulated demonstration showing how DRISHTI turns front-facing optics into metric cost representations for the trajectory planner.
            </p>
          </div>

          <div className="p-3 bg-[#151918] border border-[#252A29] rounded font-mono-tech text-xs text-[#8E9594]">
            <div className="flex items-center gap-2 text-[#54D6FF]">
              <span className="w-2 h-2 rounded-full bg-[#54D6FF]" />
              <span>SIMULATED DEMO REPRESENTATION</span>
            </div>
            <div className="text-[10px] text-[#59605F] mt-1">
              Live FastAPI backend connection scheduled for next phase
            </div>
          </div>
        </div>

        {/* 4-Stage Step Switcher */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8 font-mono-tech text-xs">
          <button
            onClick={() => setActiveView('camera')}
            className={`p-3 rounded border text-left transition-all ${
              activeView === 'camera'
                ? 'bg-[#151918] border-[#F5A623] text-[#F1F0EA]'
                : 'bg-[#101313] border-[#252A29] text-[#8E9594] hover:bg-[#151918]'
            }`}
          >
            <div className="text-[10px] text-[#59605F]">01 // SENSOR</div>
            <div className="font-bold mt-1 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-[#F5A623]" /> Camera Frame
            </div>
          </button>

          <button
            onClick={() => setActiveView('segmentation')}
            className={`p-3 rounded border text-left transition-all ${
              activeView === 'segmentation'
                ? 'bg-[#151918] border-[#39FF88] text-[#F1F0EA]'
                : 'bg-[#101313] border-[#252A29] text-[#8E9594] hover:bg-[#151918]'
            }`}
          >
            <div className="text-[10px] text-[#59605F]">02 // PERCEPTION</div>
            <div className="font-bold mt-1 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-[#39FF88]" /> Segmentation Mask
            </div>
          </button>

          <button
            onClick={() => setActiveView('costmap')}
            className={`p-3 rounded border text-left transition-all ${
              activeView === 'costmap'
                ? 'bg-[#151918] border-[#54D6FF] text-[#F1F0EA]'
                : 'bg-[#101313] border-[#252A29] text-[#8E9594] hover:bg-[#151918]'
            }`}
          >
            <div className="text-[10px] text-[#59605F]">03 // GEOMETRY</div>
            <div className="font-bold mt-1 flex items-center gap-1.5">
              <Grid className="w-3.5 h-3.5 text-[#54D6FF]" /> 2D BEV Costmap
            </div>
          </button>

          <button
            onClick={() => setActiveView('path')}
            className={`p-3 rounded border text-left transition-all ${
              activeView === 'path'
                ? 'bg-[#151918] border-[#F5A623] text-[#F1F0EA]'
                : 'bg-[#101313] border-[#252A29] text-[#8E9594] hover:bg-[#151918]'
            }`}
          >
            <div className="text-[10px] text-[#59605F]">04 // NAVIGATION</div>
            <div className="font-bold mt-1 flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-[#F5A623]" /> Safe A* Route
            </div>
          </button>
        </div>

        {/* Main Visualizer Stage Canvas Container */}
        <div className="bg-[#101313] border border-[#252A29] rounded-lg p-6 sm:p-8 corner-brackets">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Visual Canvas Frame */}
            <div className="lg:col-span-8 relative aspect-[16/10] bg-[#080909] rounded border border-[#252A29] overflow-hidden">
              
              {/* Background Base Camera Image */}
              <img
                src="/assets/terrain/camera_pov.jpg"
                alt="Camera POV on rugged outdoor trail"
                className={`w-full h-full object-cover transition-opacity duration-300 ${
                  activeView === 'costmap' ? 'opacity-20' : 'opacity-85'
                }`}
              />

              {/* Dynamic Overlays according to activeView */}
              {activeView === 'segmentation' && (
                <div className="absolute inset-0 bg-gradient-to-t from-[#39FF88]/30 via-[#54D6FF]/20 to-transparent mix-blend-screen pointer-events-none p-4">
                  <svg className="w-full h-full" viewBox="0 0 640 400" preserveAspectRatio="none">
                    <polygon points="120,400 520,400 360,180 280,180" fill="rgba(57, 255, 136, 0.4)" stroke="#39FF88" strokeWidth="1" />
                    <polygon points="0,400 120,400 280,180 0,180" fill="rgba(84, 214, 255, 0.3)" stroke="#54D6FF" strokeWidth="1" />
                    <polygon points="520,400 640,400 640,180 360,180" fill="rgba(245, 166, 35, 0.3)" stroke="#F5A623" strokeWidth="1" />
                    <rect x="310" y="240" width="50" height="40" fill="rgba(255, 77, 77, 0.6)" stroke="#FF4D4D" strokeWidth="2" />
                    <text x="315" y="235" fill="#FF4D4D" fontSize="10" fontFamily="monospace" fontWeight="bold">OBSTACLE [BLOCKED]</text>
                  </svg>
                </div>
              )}

              {activeView === 'costmap' && (
                <div className="absolute inset-0 bg-tech-grid-dense flex items-center justify-center p-6">
                  <div className="w-full h-full border border-[#252A29] rounded relative bg-[#080909]/90 p-4 font-mono-tech flex flex-col justify-between">
                    <div className="flex justify-between text-[11px] text-[#54D6FF]">
                      <span>GRID: 20x20m [100x100 CELLS]</span>
                      <span>RESOLUTION: 0.1m/px</span>
                    </div>

                    <div className="relative flex-1 my-2 flex items-center justify-center">
                      <svg className="w-full h-48" viewBox="0 0 400 200">
                        <path d="M 50 180 Q 150 120 200 100 T 350 20" fill="none" stroke="#39FF88" strokeWidth="40" strokeOpacity="0.3" />
                        <circle cx="210" cy="110" r="16" fill="#FF4D4D" fillOpacity="0.7" stroke="#FF4D4D" strokeWidth="2" />
                        <circle cx="50" cy="180" r="6" fill="#54D6FF" />
                        <circle cx="350" cy="20" r="6" fill="#F5A623" />
                      </svg>
                    </div>

                    <div className="flex justify-between text-[10px] text-[#8E9594]">
                      <span>ROVER ORIGIN (0.0, 0.0)</span>
                      <span>GOAL WAYPOINT (12.0, 18.5)</span>
                    </div>
                  </div>
                </div>
              )}

              {activeView === 'path' && (
                <div className="absolute inset-0 p-4 flex flex-col justify-between pointer-events-none">
                  <svg className="w-full h-full" viewBox="0 0 640 400" preserveAspectRatio="none">
                    <polygon points="120,400 520,400 360,180 280,180" fill="rgba(57, 255, 136, 0.15)" />
                    <rect x="310" y="240" width="50" height="40" fill="rgba(255, 77, 77, 0.6)" stroke="#FF4D4D" strokeWidth="2" />
                    <path
                      d="M 320 400 Q 250 310 270 240 T 320 180"
                      fill="none"
                      stroke="#39FF88"
                      strokeWidth="4"
                      strokeDasharray="6 3"
                    />
                    <circle cx="320" cy="390" r="8" fill="#54D6FF" stroke="#F1F0EA" strokeWidth="2" />
                    <text x="335" y="394" fill="#54D6FF" fontSize="11" fontFamily="monospace" fontWeight="bold">ROVER</text>
                    <circle cx="320" cy="180" r="8" fill="#F5A623" stroke="#F1F0EA" strokeWidth="2" />
                    <text x="335" y="184" fill="#F5A623" fontSize="11" fontFamily="monospace" fontWeight="bold">TARGET WP</text>
                  </svg>
                </div>
              )}

              <div className="absolute top-3 left-3 bg-[#080909]/90 border border-[#252A29] px-2.5 py-1 rounded text-xs font-mono-tech text-[#F1F0EA]">
                MODE: <span className="text-[#F5A623] uppercase font-bold">{activeView}</span>
              </div>
            </div>

            {/* Cost Semantics Guide */}
            <div className="lg:col-span-4 space-y-4 font-mono-tech text-xs">
              <div className="text-xs uppercase text-[#59605F] tracking-wider pb-1 border-b border-[#252A29]">
                CANONICAL COST WEIGHTS
              </div>

              <div className="space-y-2.5">
                <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#39FF88]" />
                    <span className="font-bold text-[#F1F0EA]">SMOOTH</span>
                  </div>
                  <span className="text-[#39FF88]">LOW COST (1.0)</span>
                </div>

                <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#54D6FF]" />
                    <span className="font-bold text-[#F1F0EA]">ROUGH</span>
                  </div>
                  <span className="text-[#54D6FF]">MEDIUM (3.5)</span>
                </div>

                <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#F5A623]" />
                    <span className="font-bold text-[#F1F0EA]">BUMPY</span>
                  </div>
                  <span className="text-[#F5A623]">HIGH (7.0)</span>
                </div>

                <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#FF4D4D]" />
                    <span className="font-bold text-[#F1F0EA]">OBSTACLE</span>
                  </div>
                  <span className="text-[#FF4D4D] font-bold">BLOCKED (255)</span>
                </div>

                <div className="p-2.5 bg-[#151918] border border-[#252A29] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[#E056FD]" />
                    <span className="font-bold text-[#F1F0EA]">FORBIDDEN</span>
                  </div>
                  <span className="text-[#FF4D4D] font-bold">BLOCKED (255)</span>
                </div>
              </div>

              <div className="p-3 bg-[#151918] border border-[#252A29] rounded text-[11px] text-[#8E9594] leading-relaxed">
                A* computes paths with minimum cumulative cost, naturally routing through smooth dirt while strictly avoiding obstacles with an added clearance margin.
              </div>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
};
