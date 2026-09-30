import React from 'react';
import { CheckCircle2, Clock, PlayCircle } from 'lucide-react';

interface Milestone {
  phase: string;
  title: string;
  status: 'COMPLETED' | 'ACTIVE_PHASE' | 'UPCOMING';
  description: string;
  deliverables: string[];
}

const ROADMAP_MILESTONES: Milestone[] = [
  {
    phase: 'PHASE 01',
    title: 'SIMULATION & DATASET PIPELINE',
    status: 'COMPLETED',
    description: 'SegFormer fine-tuning on RUGD/RELLIS-3D datasets, synthetic costmap formation, and basic A* search.',
    deliverables: ['6-Class traversability model', 'Ground-plane IPM projection', 'Cost-weighted A* algorithm'],
  },
  {
    phase: 'PHASE 02',
    title: 'REAL FOOTAGE & CLOSED-LOOP VALIDATION',
    status: 'ACTIVE_PHASE',
    description: 'Processing recorded outdoor phone footage, feature-based visual odometry pose tracking, and closed-loop dynamic replan verification.',
    deliverables: ['OpenCV VO with inlier confidence', 'Obstacle insertion & path invalidation', 'Pure Pursuit kinematic controller'],
  },
  {
    phase: 'PHASE 03',
    title: 'INTEGRATED TELEMETRY SERVER',
    status: 'ACTIVE_PHASE',
    description: 'FastAPI and WebSocket streaming bridge connecting the Python navigation stack to the React Mission Control.',
    deliverables: ['Real-time frame broadcast', 'Telemetry WebSocket protocol', 'Mission event streaming'],
  },
  {
    phase: 'PHASE 04',
    title: 'PHYSICAL UGV EMBODIMENT',
    status: 'UPCOMING',
    description: 'Mounting camera hardware onto physical tracked rover chassis, executing onboard or tethered laptop navigation.',
    deliverables: ['Serial motor driver interface', 'Onboard camera mount & calibration', 'Physical outdoor test corridor'],
  },
  {
    phase: 'PHASE 05',
    title: 'FIELD DEPLOYMENT & HARDENING',
    status: 'UPCOMING',
    description: 'Long-range cross-country navigation in complex unstructured outdoor terrain under variable lighting and adverse conditions.',
    deliverables: ['Extended domain-shift evaluation', 'Multi-scenario safety e-stop testing', 'Operator field deployment handbook'],
  },
];

export const Roadmap: React.FC = () => {
  return (
    <section id="roadmap" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>11 — PROJECT ROADMAP</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
            THE PATH TO FIELD DEPLOYMENT
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            Structured engineering roadmap from core simulation algorithms to physical unmanned vehicle locomotion.
          </p>
        </div>

        {/* Vertical Timeline */}
        <div className="relative border-l border-[#252A29] ml-4 sm:ml-8 pl-6 sm:pl-10 space-y-12">
          {ROADMAP_MILESTONES.map((m, idx) => {
            let statusTag = null;
            if (m.status === 'COMPLETED') {
              statusTag = (
                <span className="badge-status badge-green">
                  <CheckCircle2 className="w-3 h-3" /> VERIFIED
                </span>
              );
            } else if (m.status === 'ACTIVE_PHASE') {
              statusTag = (
                <span className="badge-status badge-amber">
                  <PlayCircle className="w-3 h-3" /> CURRENT MILESTONE
                </span>
              );
            } else {
              statusTag = (
                <span className="badge-status badge-cyan">
                  <Clock className="w-3 h-3" /> PLANNED
                </span>
              );
            }

            return (
              <div key={idx} className="relative group">
                <div
                  className={`absolute -left-[31px] sm:-left-[47px] top-1 w-5 h-5 rounded-full border-2 bg-[#080909] flex items-center justify-center ${
                    m.status === 'COMPLETED'
                      ? 'border-[#39FF88] text-[#39FF88]'
                      : m.status === 'ACTIVE_PHASE'
                      ? 'border-[#F5A623] text-[#F5A623]'
                      : 'border-[#59605F] text-[#59605F]'
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      m.status === 'COMPLETED'
                        ? 'bg-[#39FF88]'
                        : m.status === 'ACTIVE_PHASE'
                        ? 'bg-[#F5A623] animate-ping'
                        : 'bg-[#59605F]'
                    }`}
                  />
                </div>

                <div className="p-6 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets hover:border-[#38403e] transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
                    <span className="font-mono-tech text-xs text-[#F5A623] font-bold">
                      {m.phase}
                    </span>
                    {statusTag}
                  </div>

                  <h3 className="font-heading font-bold text-xl text-[#F1F0EA] mb-2">
                    {m.title}
                  </h3>

                  <p className="text-sm text-[#8E9594] mb-4 leading-relaxed">
                    {m.description}
                  </p>

                  <div className="pt-3 border-t border-[#1c2221] flex flex-wrap gap-2 font-mono-tech text-xs">
                    {m.deliverables.map((deliv, dIdx) => (
                      <span
                        key={dIdx}
                        className="px-2.5 py-1 bg-[#151918] border border-[#252A29] rounded text-[#8E9594]"
                      >
                        ✓ {deliv}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
};
