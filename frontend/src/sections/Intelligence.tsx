import React from 'react';
import { Eye, Navigation, Compass } from 'lucide-react';
import { INITIAL_CLASSES } from '../lib/prototypeData';

export const Intelligence: React.FC = () => {
  return (
    <section id="intelligence" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>05 — INTELLIGENCE & REASONING</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
            THREE CORE REASONING ENGINES
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            DRISHTI decomposes autonomous cross-country locomotion into three unambiguous questions answered at 20+ Hz.
          </p>
        </div>

        {/* Engine 1: PERCEPTION */}
        <div className="mb-12 p-6 sm:p-8 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-[#252A29]">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded bg-[#151918] border border-[#39FF88]/40 flex items-center justify-center text-[#39FF88]">
                <Eye className="w-6 h-6" />
              </div>
              <div>
                <div className="font-mono-tech text-xs text-[#39FF88] uppercase tracking-wider">ENGINE 01 // PERCEPTION</div>
                <h3 className="font-heading font-bold text-2xl sm:text-3xl text-[#F1F0EA]">
                  “What can I drive on?”
                </h3>
              </div>
            </div>
            <div className="font-mono-tech text-xs text-[#8E9594] bg-[#151918] px-3 py-1.5 rounded border border-[#252A29]">
              SegFormer-B0 Backbone (RUGD + RELLIS-3D)
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            <div className="lg:col-span-4 space-y-3">
              <p className="text-sm text-[#8E9594] leading-relaxed">
                Rather than treating raw objects generically, DRISHTI maps visual semantics directly into six rigorous traversability groups with assigned mechanical cost weights.
              </p>
              <div className="p-3 bg-[#151918] border border-[#252A29] rounded font-mono-tech text-xs text-[#59605F] space-y-1">
                <div>UNKNOWN/LOW-CONFIDENCE:</div>
                <div className="text-[#F5A623]">Handled as high cost state rather than 7th class</div>
              </div>
            </div>

            {/* 6 Navigability Groups Grid */}
            <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {INITIAL_CLASSES.map((cls) => (
                <div
                  key={cls.name}
                  className="p-3 bg-[#151918] border border-[#252A29] rounded font-mono-tech transition-all hover:border-[#38403e]"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: cls.color }} />
                      <span className="text-xs font-bold text-[#F1F0EA]">{cls.name}</span>
                    </div>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded border ${
                        cls.isTraversable
                          ? 'text-[#39FF88] border-[#39FF88]/30 bg-[#39FF88]/10'
                          : 'text-[#FF4D4D] border-[#FF4D4D]/30 bg-[#FF4D4D]/10'
                      }`}
                    >
                      {cls.costWeight === 'BLOCKED' ? 'BLOCKED' : `COST: ${cls.costWeight}`}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#8E9594] leading-snug">
                    {cls.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Engine 2 & 3: LOCALIZATION and PLANNING */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Engine 2: LOCALIZATION */}
          <div className="p-6 sm:p-8 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded bg-[#151918] border border-[#54D6FF]/40 flex items-center justify-center text-[#54D6FF]">
                  <Navigation className="w-6 h-6" />
                </div>
                <div>
                  <div className="font-mono-tech text-xs text-[#54D6FF] uppercase tracking-wider">ENGINE 02 // LOCALIZATION</div>
                  <h3 className="font-heading font-bold text-2xl text-[#F1F0EA]">
                    “Where am I?”
                  </h3>
                </div>
              </div>

              <p className="text-sm text-[#8E9594] leading-relaxed mb-6">
                In satellite-denied environments, DRISHTI uses monocular/stereo Visual Odometry (VO) tracking sparse visual features across successive video frames to reconstruct displacement and heading.
              </p>

              <div className="space-y-3 font-mono-tech text-xs bg-[#151918] p-4 rounded border border-[#252A29]">
                <div className="flex justify-between py-1 border-b border-[#252A29]">
                  <span className="text-[#8E9594]">Optical Flow Tracking:</span>
                  <span className="text-[#54D6FF]">Lucas-Kanade / FAST</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252A29]">
                  <span className="text-[#8E9594]">Motion Estimation:</span>
                  <span className="text-[#F1F0EA]">5-Point RANSAC Essential Matrix</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#8E9594]">Confidence Metric:</span>
                  <span className="text-[#39FF88]">Inlier Count & Epipolar Residuals</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[#1c2221] font-mono-tech text-[11px] text-[#59605F] flex items-center justify-between">
              <span>GPS: COMPLETELY DISCONNECTED</span>
              <span className="text-[#54D6FF]">DRIFT-AWARE</span>
            </div>
          </div>

          {/* Engine 3: PLANNING */}
          <div className="p-6 sm:p-8 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded bg-[#151918] border border-[#F5A623]/40 flex items-center justify-center text-[#F5A623]">
                  <Compass className="w-6 h-6" />
                </div>
                <div>
                  <div className="font-mono-tech text-xs text-[#F5A623] uppercase tracking-wider">ENGINE 03 // PLANNING & REPLAN</div>
                  <h3 className="font-heading font-bold text-2xl text-[#F1F0EA]">
                    “Where should I go?”
                  </h3>
                </div>
              </div>

              <p className="text-sm text-[#8E9594] leading-relaxed mb-6">
                A* path planning computes least-effort trajectories over the 2D traversability costmap. If a sudden obstacle appears in front of the vehicle, the route is invalidated instantly and replanned.
              </p>

              <div className="space-y-3 font-mono-tech text-xs bg-[#151918] p-4 rounded border border-[#252A29]">
                <div className="flex justify-between py-1 border-b border-[#252A29]">
                  <span className="text-[#8E9594]">Objective Function:</span>
                  <span className="text-[#F5A623]">Min [Distance + Terrain Cost]</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252A29]">
                  <span className="text-[#8E9594]">Dynamic Replanning:</span>
                  <span className="text-[#39FF88]">&lt;20ms On Obstacle Trigger</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#8E9594]">Tracking Controller:</span>
                  <span className="text-[#F1F0EA]">Pure Pursuit with Lookahead</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[#1c2221] font-mono-tech text-[11px] text-[#59605F] flex items-center justify-between">
              <span>COLLISION-CHECK: 20 HZ</span>
              <span className="text-[#39FF88]">CLOSED-LOOP VALIDATED</span>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
};
