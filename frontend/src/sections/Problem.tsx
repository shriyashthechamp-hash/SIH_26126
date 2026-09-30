import React from 'react';
import { Eye, Navigation, Compass, ShieldCheck, MapPinOff } from 'lucide-react';

export const Problem: React.FC = () => {
  return (
    <section id="problem" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>03 — THE PROBLEM DEFINITION</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA] leading-tight">
            WHEN GPS DISAPPEARS,<br />
            <span className="text-[#8E9594]">THE WORLD DOESN’T.</span>
          </h2>
          <p className="mt-5 text-base sm:text-lg text-[#8E9594] leading-relaxed">
            Outdoor tactical, agricultural, and search environments contain rough ground, steep ditches, and unmapped obstacles where satellite signals are spoofed, occluded, or completely denied.
            DRISHTI overcomes satellite dependency through optical autonomy: camera-first terrain segmentation, visual odometry, ground-plane costmaps, and real-time path planning.
          </p>
        </div>

        {/* 3 Core Pillars: SEE, KNOW, MOVE */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Pillar 1: SEE */}
          <div className="p-6 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets group hover:border-[#F5A623]/50 transition-all">
            <div className="flex items-center justify-between mb-6">
              <div className="w-10 h-10 rounded bg-[#151918] border border-[#252A29] flex items-center justify-center text-[#F5A623] group-hover:border-[#F5A623] transition-colors">
                <Eye className="w-5 h-5" />
              </div>
              <span className="font-mono-tech text-xs text-[#59605F] uppercase">PILLAR 01</span>
            </div>

            <div className="space-y-2">
              <span className="font-mono-tech text-xs font-semibold text-[#F5A623] tracking-widest uppercase">
                01 // PERCEPTION
              </span>
              <h3 className="font-heading font-bold text-2xl text-[#F1F0EA]">SEE</h3>
              <p className="font-mono-tech text-sm text-[#39FF88]">Understand the terrain.</p>
            </div>

            <p className="mt-4 text-sm text-[#8E9594] leading-relaxed">
              Real-time deep semantic segmentation converts raw camera pixels into 6 structured traversability classes: Smooth, Rough, Bumpy, Forbidden, Obstacle, and Background.
            </p>

            <div className="mt-6 pt-4 border-t border-[#1c2221] flex items-center justify-between font-mono-tech text-[11px] text-[#59605F]">
              <span>SegFormer-B0</span>
              <span className="text-[#39FF88]">640x512 @ 22+ FPS</span>
            </div>
          </div>

          {/* Pillar 2: KNOW */}
          <div className="p-6 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets group hover:border-[#54D6FF]/50 transition-all">
            <div className="flex items-center justify-between mb-6">
              <div className="w-10 h-10 rounded bg-[#151918] border border-[#252A29] flex items-center justify-center text-[#54D6FF] group-hover:border-[#54D6FF] transition-colors">
                <Navigation className="w-5 h-5" />
              </div>
              <span className="font-mono-tech text-xs text-[#59605F] uppercase">PILLAR 02</span>
            </div>

            <div className="space-y-2">
              <span className="font-mono-tech text-xs font-semibold text-[#54D6FF] tracking-widest uppercase">
                02 // LOCALIZATION
              </span>
              <h3 className="font-heading font-bold text-2xl text-[#F1F0EA]">KNOW</h3>
              <p className="font-mono-tech text-sm text-[#54D6FF]">Estimate where the vehicle is.</p>
            </div>

            <p className="mt-4 text-sm text-[#8E9594] leading-relaxed">
              Monocular / stereo visual odometry continuously computes frame-to-frame 6-DoF vehicle pose and tracking quality scores without relying on satellite coordinates or external anchors.
            </p>

            <div className="mt-6 pt-4 border-t border-[#1c2221] flex items-center justify-between font-mono-tech text-[11px] text-[#59605F]">
              <span>OpenCV VO</span>
              <span className="text-[#54D6FF]">Pose X, Y, Yaw + Inliers</span>
            </div>
          </div>

          {/* Pillar 3: MOVE */}
          <div className="p-6 bg-[#101313] border border-[#252A29] rounded-lg corner-brackets group hover:border-[#39FF88]/50 transition-all">
            <div className="flex items-center justify-between mb-6">
              <div className="w-10 h-10 rounded bg-[#151918] border border-[#252A29] flex items-center justify-center text-[#39FF88] group-hover:border-[#39FF88] transition-colors">
                <Compass className="w-5 h-5" />
              </div>
              <span className="font-mono-tech text-xs text-[#59605F] uppercase">PILLAR 03</span>
            </div>

            <div className="space-y-2">
              <span className="font-mono-tech text-xs font-semibold text-[#39FF88] tracking-widest uppercase">
                03 // PLANNING & CONTROL
              </span>
              <h3 className="font-heading font-bold text-2xl text-[#F1F0EA]">MOVE</h3>
              <p className="font-mono-tech text-sm text-[#39FF88]">Plan and follow a safe route.</p>
            </div>

            <p className="mt-4 text-sm text-[#8E9594] leading-relaxed">
              Cost-aware A* path planning routes around high-resistance or hazardous terrain. Pure Pursuit controller commands steering and throttles speed, instantly replanning if obstacles appear.
            </p>

            <div className="mt-6 pt-4 border-t border-[#1c2221] flex items-center justify-between font-mono-tech text-[11px] text-[#59605F]">
              <span>Costmap A* + Pure Pursuit</span>
              <span className="text-[#F5A623]">Dynamic Replanning</span>
            </div>
          </div>

        </div>

        {/* GPS-Denied Operational Context Banner */}
        <div className="mt-12 p-5 bg-[#151918] border border-[#252A29] rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 font-mono-tech text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#FF4D4D]/10 text-[#FF4D4D] rounded border border-[#FF4D4D]/30">
              <MapPinOff className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[#F1F0EA] font-medium">GPS-DENIED ASSUMPTION: </span>
              <span className="text-[#8E9594]">No RTK, no GNSS waypoints, no external motion capture.</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[#39FF88]">
            <ShieldCheck className="w-4 h-4" />
            <span>EXPLAINABLE & FAIL-SAFE</span>
          </div>
        </div>

      </div>
    </section>
  );
};
