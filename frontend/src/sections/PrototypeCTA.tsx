import React from 'react';
import { Activity, ArrowRight } from 'lucide-react';

interface PrototypeCTAProps {
  onOpenPrototype: () => void;
}

export const PrototypeCTA: React.FC<PrototypeCTAProps> = ({ onOpenPrototype }) => {
  return (
    <section className="py-24 bg-[#101313] border-b border-[#252A29] relative overflow-hidden">
      <div className="absolute inset-0 bg-tech-grid opacity-30 pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-[#F5A623]/5 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#151918] border border-[#252A29] rounded text-xs font-mono-tech text-[#F5A623] mb-6">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span>MISSION CONTROL SIMULATOR</span>
        </div>

        <h2 className="font-heading font-extrabold text-4xl sm:text-6xl tracking-tight text-[#F1F0EA] max-w-3xl mx-auto">
          SEE DRISHTI THINK.
        </h2>

        <p className="mt-5 text-base sm:text-lg text-[#8E9594] max-w-xl mx-auto leading-relaxed">
          Enter the interactive mission control environment to inspect simulated camera perception, top-down BEV costmap generation, and live A* dynamic obstacle replanning.
        </p>

        <div className="mt-8 flex justify-center">
          <button
            onClick={onOpenPrototype}
            className="btn-primary py-4 px-8 text-sm font-bold flex items-center gap-2.5 shadow-xl hover:scale-105"
          >
            <span>TEST THE PROTOTYPE</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-6 font-mono-tech text-xs text-[#59605F]">
          <span>STANDALONE CLIENT RUNTIME</span>
          <span>•</span>
          <span>NO CAMERA PERMISSION REQUIRED</span>
          <span>•</span>
          <span>DETERMINISTIC EVENT REPLAY</span>
        </div>

      </div>
    </section>
  );
};
