import React from 'react';
import { ArrowRight, ChevronDown, Radio, Eye, Crosshair, Compass } from 'lucide-react';

interface HeroProps {
  onExploreSystem: () => void;
  onOpenPrototype: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onExploreSystem, onOpenPrototype }) => {
  return (
    <section className="relative min-h-screen pt-24 pb-16 flex flex-col justify-between overflow-hidden bg-tech-grid border-b border-[#252A29]">
      {/* Background Ambience & Gradient Mesh */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#080909]/60 via-transparent to-[#080909] pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#F5A623]/5 blur-[120px] rounded-full pointer-events-none" />

      {/* Hero Content Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 w-full flex-1 flex flex-col justify-center my-auto">
        
        {/* Top Status Bar Telemetry */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8 py-2 px-4 bg-[#101313]/80 border border-[#252A29] rounded font-mono-tech text-xs">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-[#8E9594]">GPS:</span>
              <span className="text-[#FF4D4D] font-bold flex items-center gap-1">
                <Radio className="w-3 h-3 animate-pulse" /> DISABLED
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#8E9594]">PERCEPTION:</span>
              <span className="text-[#39FF88] flex items-center gap-1">
                <Eye className="w-3 h-3" /> ONLINE (SegFormer)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#8E9594]">LOCALIZATION:</span>
              <span className="text-[#54D6FF] flex items-center gap-1">
                <Crosshair className="w-3 h-3" /> READY (VO)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#8E9594]">PLANNER:</span>
              <span className="text-[#F5A623] flex items-center gap-1">
                <Compass className="w-3 h-3" /> READY (A*)
              </span>
            </div>
          </div>
          <div className="text-[#59605F] text-[11px] hidden sm:block">
            LATENCY: &lt;45ms // BEV: 20x20m
          </div>
        </div>

        {/* Main Grid: Headline & Cinematic Visual */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          
          {/* Left Column: Editorial Headline & Copy */}
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#151918] border border-[#252A29] rounded text-xs font-mono-tech text-[#F5A623]">
              <span className="w-2 h-2 rounded-full bg-[#F5A623] animate-ping" />
              <span>SIH 26126 — AUTONOMOUS ROBOTICS</span>
            </div>

            <h1 className="font-heading font-extrabold text-4xl sm:text-6xl xl:text-7xl leading-[1.04] tracking-tight text-[#F1F0EA]">
              SEE THE TERRAIN.<br />
              <span className="text-[#F5A623]">FIND THE PATH.</span><br />
              MOVE WITHOUT GPS.
            </h1>

            <p className="text-base sm:text-lg text-[#8E9594] font-normal max-w-xl leading-relaxed">
              Camera-first autonomous navigation for unmanned ground vehicles operating in GPS-denied environments.
              Transforms visual terrain understanding into explainable, confidence-aware navigation decisions.
            </p>

            {/* CTA Action Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-4">
              <button
                onClick={onOpenPrototype}
                className="btn-primary"
              >
                <span>TEST THE PROTOTYPE</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={onExploreSystem}
                className="btn-secondary"
              >
                <span>EXPLORE THE SYSTEM</span>
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>

            {/* Small Technical Annotations */}
            <div className="pt-6 border-t border-[#1c2221] grid grid-cols-3 gap-4 font-mono-tech text-xs">
              <div>
                <div className="text-[#59605F] text-[10px] uppercase">Terrain Sensing</div>
                <div className="text-[#F1F0EA] font-medium mt-0.5">6 Nav Groups</div>
              </div>
              <div>
                <div className="text-[#59605F] text-[10px] uppercase">Localization</div>
                <div className="text-[#F1F0EA] font-medium mt-0.5">Visual Odometry</div>
              </div>
              <div>
                <div className="text-[#59605F] text-[10px] uppercase">Replanning</div>
                <div className="text-[#39FF88] font-medium mt-0.5">Cost-Aware A*</div>
              </div>
            </div>
          </div>

          {/* Right Column: Cinematic UGV & Perception HUD Graphic */}
          <div className="lg:col-span-6 relative">
            <div className="relative rounded-lg border border-[#252A29] bg-[#101313] p-2 corner-brackets overflow-hidden group shadow-2xl">
              
              {/* Cinematic Image Frame */}
              <div className="relative aspect-[16/10] rounded overflow-hidden bg-[#080909]">
                <img
                  src="/assets/hero/ugv_hero.jpg"
                  alt="DRISHTI Unmanned Ground Vehicle navigating rugged terrain"
                  className="w-full h-full object-cover object-center filter contrast-105 brightness-95 group-hover:scale-105 transition-transform duration-700"
                  onError={(e) => {
                    // Fallback placeholder if image load encounters issues
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />

                {/* Scanline overlay */}
                <div className="scanlines absolute inset-0 pointer-events-none" />

                {/* HUD HUD Overlay Graphics */}
                <div className="absolute inset-0 p-4 flex flex-col justify-between pointer-events-none font-mono-tech">
                  
                  {/* Top HUD markers */}
                  <div className="flex items-center justify-between text-[11px] text-[#54D6FF] bg-[#080909]/70 px-2.5 py-1 rounded border border-[#252A29]/80 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#39FF88]" />
                      <span>CAM_01: STEREO FORWARD</span>
                    </div>
                    <span>RES: 640x512 @ 22.4 FPS</span>
                  </div>

                  {/* Center Reticle and Trajectory Projection */}
                  <div className="relative flex items-center justify-center">
                    <div className="w-24 h-24 border border-dashed border-[#F5A623]/40 rounded-full flex items-center justify-center">
                      <div className="w-3 h-3 border border-[#F5A623] rounded-sm" />
                    </div>
                    {/* Simulated Waypoint vector */}
                    <div className="absolute bottom-[-10px] w-32 h-1 bg-gradient-to-r from-transparent via-[#39FF88] to-transparent opacity-80" />
                  </div>

                  {/* Bottom HUD telemetry */}
                  <div className="flex items-center justify-between text-[10px] text-[#F1F0EA] bg-[#080909]/80 p-2 rounded border border-[#252A29] backdrop-blur-sm">
                    <div className="space-y-0.5">
                      <div className="text-[#8E9594]">TERRAIN CLASSIFICATION</div>
                      <div className="text-[#39FF88] font-bold">DIRT TRAIL // SMOOTH (0.94)</div>
                    </div>
                    <div className="text-right space-y-0.5">
                      <div className="text-[#8E9594]">ACTIVE CORRIDOR</div>
                      <div className="text-[#F5A623] font-bold">CLEARANCE: 1.25m</div>
                    </div>
                  </div>

                </div>

                {/* Reticle Sweep Line */}
                <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#54D6FF]/60 to-transparent reticle-sweep pointer-events-none" />
              </div>

              {/* Technical Caption Below Frame */}
              <div className="mt-2.5 px-2 flex items-center justify-between font-mono-tech text-[10px] text-[#8E9594]">
                <span>FIG 01.1 — FIELD NAVIGATION EMBODIMENT</span>
                <span className="text-[#F5A623]">UGV STEREO PAYLOAD</span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* Bottom Scroll Indicator */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full pt-8 flex items-center justify-between font-mono-tech text-[11px] text-[#59605F]">
        <div className="flex items-center gap-2">
          <span>COORDINATES:</span>
          <span className="text-[#8E9594]">N 18°31'49" E 73°51'11" [DENIED]</span>
        </div>
        <button
          onClick={onExploreSystem}
          className="flex items-center gap-1.5 text-[#8E9594] hover:text-[#F5A623] transition-colors"
        >
          <span>SCROLL FOR PIPELINE</span>
          <ChevronDown className="w-3.5 h-3.5 animate-bounce" />
        </button>
      </div>
    </section>
  );
};
