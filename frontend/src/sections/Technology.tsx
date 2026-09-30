import React from 'react';
import { CheckCircle2, RefreshCw, Clock } from 'lucide-react';

interface TechItem {
  name: string;
  category: 'Perception & Datasets' | 'Localization & Mapping' | 'Planning & Control' | 'Simulation & Interface';
  status: 'IMPLEMENTED' | 'INTEGRATION' | 'SIMULATION' | 'PLANNED';
  description: string;
}

const TECH_STACK: TechItem[] = [
  {
    name: 'SegFormer-B0',
    category: 'Perception & Datasets',
    status: 'IMPLEMENTED',
    description: 'Lightweight hierarchical vision transformer backbone for efficient pixel segmentation.',
  },
  {
    name: 'RUGD Dataset',
    category: 'Perception & Datasets',
    status: 'IMPLEMENTED',
    description: 'Robot Unstructured Ground Driving benchmark dataset for outdoor cross-country trails.',
  },
  {
    name: 'RELLIS-3D Dataset',
    category: 'Perception & Datasets',
    status: 'IMPLEMENTED',
    description: 'Multimodal off-road dataset providing rugged terrain and vegetation semantic classes.',
  },
  {
    name: 'OpenCV Feature VO',
    category: 'Localization & Mapping',
    status: 'IMPLEMENTED',
    description: 'Optical flow and feature matching for continuous 6-DoF vehicle pose estimation.',
  },
  {
    name: 'BEV Homography / IPM',
    category: 'Localization & Mapping',
    status: 'IMPLEMENTED',
    description: 'Inverse Perspective Mapping projecting perspective segmentation to top-down ground plane.',
  },
  {
    name: '2D Traversability Costmap',
    category: 'Localization & Mapping',
    status: 'IMPLEMENTED',
    description: 'Rolling 100x100 metric grid (0.1m/px) encoding smooth, rough, bumpy, and obstacle costs.',
  },
  {
    name: 'Cost-Weighted A*',
    category: 'Planning & Control',
    status: 'IMPLEMENTED',
    description: 'Dynamic graph search finding least-resistance trajectories with clearance buffers.',
  },
  {
    name: 'Pure Pursuit Controller',
    category: 'Planning & Control',
    status: 'IMPLEMENTED',
    description: 'Geometric path tracking controller generating linear & angular velocity commands.',
  },
  {
    name: 'Webots Simulation',
    category: 'Simulation & Interface',
    status: 'SIMULATION',
    description: 'Physics-based virtual test environment for closed-loop evaluation before rover deployment.',
  },
  {
    name: 'FastAPI + WebSocket',
    category: 'Simulation & Interface',
    status: 'INTEGRATION',
    description: 'High-throughput async backend server streaming live telemetry to the mission dashboard.',
  },
  {
    name: 'React 18 + Vite + TS',
    category: 'Simulation & Interface',
    status: 'IMPLEMENTED',
    description: 'Modular, high-performance telemetry dashboard and public deployment interface.',
  },
];

export const Technology: React.FC = () => {
  return (
    <section id="technology" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>09 — TECHNICAL STACK & STATUS</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA]">
            ENGINEERED COMPONENTS
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            Transparent component-level verification status across DRISHTI’s perception, localization, planning, and web layers.
          </p>
        </div>

        {/* Tech Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {TECH_STACK.map((tech) => {
            let statusBadge = null;
            if (tech.status === 'IMPLEMENTED') {
              statusBadge = (
                <span className="badge-status badge-green">
                  <CheckCircle2 className="w-3 h-3" /> IMPLEMENTED
                </span>
              );
            } else if (tech.status === 'INTEGRATION') {
              statusBadge = (
                <span className="badge-status badge-amber">
                  <RefreshCw className="w-3 h-3" /> INTEGRATION
                </span>
              );
            } else {
              statusBadge = (
                <span className="badge-status badge-cyan">
                  <Clock className="w-3 h-3" /> {tech.status}
                </span>
              );
            }

            return (
              <div
                key={tech.name}
                className="p-5 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets flex flex-col justify-between hover:border-[#38403e] transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="font-mono-tech text-[10px] text-[#59605F] uppercase tracking-wider">
                      {tech.category}
                    </span>
                    {statusBadge}
                  </div>

                  <h3 className="font-heading font-bold text-lg text-[#F1F0EA] mb-2">
                    {tech.name}
                  </h3>

                  <p className="text-xs text-[#8E9594] leading-relaxed">
                    {tech.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-[#1c2221] font-mono-tech text-[10px] text-[#59605F]">
                  REPO PATH: src/
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
};
