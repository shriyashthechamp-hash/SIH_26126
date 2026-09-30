import React, { useState } from 'react';
import { AlertCircle, ShieldAlert, CheckCircle } from 'lucide-react';

export const Confidence: React.FC = () => {
  const [activeTier, setActiveTier] = useState<0 | 1 | 2>(0);

  const tiers = [
    {
      state: 'HIGH CONFIDENCE // TRACKING',
      color: '#39FF88',
      borderColor: 'border-[#39FF88]',
      badgeColor: 'text-[#39FF88] bg-[#39FF88]/10 border-[#39FF88]/30',
      perceptionConfidence: '0.92 - 0.98',
      voInliers: '>180 inliers',
      vehicleResponse: 'Nominal Speed (0.6 m/s)',
      action: 'Pure Pursuit tracks primary A* trajectory with full lookahead buffer.',
      icon: <CheckCircle className="w-5 h-5 text-[#39FF88]" />,
    },
    {
      state: 'DEGRADED // LOW CONFIDENCE',
      color: '#F5A623',
      borderColor: 'border-[#F5A623]',
      badgeColor: 'text-[#F5A623] bg-[#F5A623]/10 border-[#F5A623]/30',
      perceptionConfidence: '0.65 - 0.91',
      voInliers: '80 - 180 inliers',
      vehicleResponse: 'Throttle Speed to 50% (0.3 m/s)',
      action: 'Expands obstacle inflation radius; applies conservative waypoint lookahead.',
      icon: <AlertCircle className="w-5 h-5 text-[#F5A623]" />,
    },
    {
      state: 'STOP // LOCALIZATION LOST',
      color: '#FF4D4D',
      borderColor: 'border-[#FF4D4D]',
      badgeColor: 'text-[#FF4D4D] bg-[#FF4D4D]/10 border-[#FF4D4D]/30',
      perceptionConfidence: '< 0.65',
      voInliers: '<80 inliers or VO fail',
      vehicleResponse: 'E-Stop Triggered (0.0 m/s)',
      action: 'Safe halt; logs diagnostic and executes stationary feature re-acquisition scan.',
      icon: <ShieldAlert className="w-5 h-5 text-[#FF4D4D]" />,
    },
  ];

  return (
    <section id="confidence" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>08 — CONFIDENCE GATING & SAFETY STATES</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
            CONFIDENCE-AWARE NAVIGATION
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            Real field robotics requires humility under uncertainty. DRISHTI continuously scales rover velocity and clearance based on perception entropy and visual odometry tracking quality.
          </p>
        </div>

        {/* 3 Interactive Tier Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {tiers.map((t, idx) => {
            const isSelected = activeTier === idx;
            return (
              <div
                key={idx}
                onClick={() => setActiveTier(idx as 0 | 1 | 2)}
                className={`p-6 rounded-lg bg-[#101313] border cursor-pointer transition-all corner-brackets ${
                  isSelected ? `${t.borderColor} bg-[#151918]` : 'border-[#252A29] hover:border-[#38403e]'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  {t.icon}
                  <span className={`font-mono-tech text-[10px] uppercase px-2 py-0.5 rounded border ${t.badgeColor}`}>
                    TIER 0{idx + 1}
                  </span>
                </div>

                <h3 className="font-heading font-bold text-lg text-[#F1F0EA] mb-3">
                  {t.state}
                </h3>

                <p className="text-xs text-[#8E9594] leading-relaxed mb-6">
                  {t.action}
                </p>

                <div className="space-y-2 font-mono-tech text-xs pt-4 border-t border-[#1c2221]">
                  <div className="flex justify-between text-[#8E9594]">
                    <span>Segmentation:</span>
                    <span className="text-[#F1F0EA]">{t.perceptionConfidence}</span>
                  </div>
                  <div className="flex justify-between text-[#8E9594]">
                    <span>VO Inliers:</span>
                    <span className="text-[#F1F0EA]">{t.voInliers}</span>
                  </div>
                  <div className="flex justify-between text-[#8E9594]">
                    <span>Actuation:</span>
                    <span style={{ color: t.color }} className="font-bold">{t.vehicleResponse}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Status Disclaimer */}
        <div className="p-4 bg-[#101313] border border-[#252A29] rounded flex items-center justify-between font-mono-tech text-xs text-[#59605F]">
          <span>CONFIDENCE GATING SUBSYSTEM: SPECIFICATION TEST PROTOCOL (§13)</span>
          <span className="text-[#F5A623]">DEMO MODE</span>
        </div>

      </div>
    </section>
  );
};
