import React from 'react';
import { AlertTriangle, ShieldCheck, FileText, Activity } from 'lucide-react';

export const Explainability: React.FC = () => {
  return (
    <section id="explainability" className="py-24 bg-[#080909] border-b border-[#252A29] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-2 font-mono-tech text-xs text-[#F5A623] mb-3">
            <span className="w-1.5 h-1.5 bg-[#F5A623] rounded-full" />
            <span>07 — EXPLAINABLE AUTONOMY</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-5xl tracking-tight text-[#F1F0EA] leading-tight">
            DON’T JUST FIND A ROUTE.<br />
            <span className="text-[#F5A623]">EXPLAIN IT.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#8E9594]">
            Black-box autonomy is a liability in real outdoor environments. DRISHTI structures every navigation choice into an auditable, human-interpretable reasoning record.
          </p>
        </div>

        {/* Explainability Grid: Mock Decision Telemetry + Core Rationale */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Column: Mock Route Decision Panel */}
          <div className="lg:col-span-7 bg-[#101313] border border-[#252A29] rounded-lg p-6 sm:p-8 corner-brackets">
            
            <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#252A29] font-mono-tech">
              <div className="flex items-center gap-2 text-xs text-[#F1F0EA]">
                <Activity className="w-4 h-4 text-[#F5A623]" />
                <span className="font-bold">REPLAN REASONING RECORD</span>
              </div>
              <span className="text-[10px] text-[#54D6FF] px-2 py-0.5 bg-[#54D6FF]/10 border border-[#54D6FF]/30 rounded">
                ILLUSTRATIVE INTERFACE
              </span>
            </div>

            {/* Decision Status Breakdown */}
            <div className="space-y-4 font-mono-tech">
              
              {/* Event 1: Route Invalidation */}
              <div className="p-4 bg-[#151918] border border-[#FF4D4D]/40 rounded">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-[#8E9594]">ORIGINAL NOMINAL PATH:</span>
                  <span className="text-[#FF4D4D] font-bold px-2 py-0.5 bg-[#FF4D4D]/10 rounded border border-[#FF4D4D]/30">
                    BLOCKED
                  </span>
                </div>
                <div className="text-sm text-[#F1F0EA]">
                  <span className="text-[#FF4D4D] font-bold">REASON:</span> 14 blocked cells detected at +4.8m in nominal corridor
                </div>
              </div>

              {/* Event 2: Safe Alternative Synthesis */}
              <div className="p-4 bg-[#151918] border border-[#39FF88]/40 rounded">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-[#8E9594]">SELECTED BYPASS ROUTE:</span>
                  <span className="text-[#39FF88] font-bold px-2 py-0.5 bg-[#39FF88]/10 rounded border border-[#39FF88]/30">
                    VALID // COMMITTED
                  </span>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs">
                  <div>
                    <div className="text-[#59605F]">PATH PENALTY:</div>
                    <div className="text-[#F1F0EA] font-bold">+3.5 m length</div>
                  </div>
                  <div>
                    <div className="text-[#59605F]">MIN CLEARANCE:</div>
                    <div className="text-[#39FF88] font-bold">0.9 m buffer</div>
                  </div>
                  <div>
                    <div className="text-[#59605F]">POSE CONFIDENCE:</div>
                    <div className="text-[#54D6FF] font-bold">0.82 (High)</div>
                  </div>
                </div>
              </div>

              {/* Action Vector Log */}
              <div className="p-3 bg-[#080909] border border-[#252A29] rounded text-xs space-y-1.5 text-[#8E9594]">
                <div className="flex items-center justify-between text-[11px]">
                  <span>REPLAN LATENCY: 18.4 ms</span>
                  <span className="text-[#39FF88]">A* EXPLORED: 412 NODES</span>
                </div>
                <div className="text-[11px] text-[#59605F] truncate">
                  &gt; [CMD] STEER: -0.14 rad // SPEED: 0.35 m/s // REASON: Smooth left gravel bypass
                </div>
              </div>

            </div>

            <div className="mt-4 pt-3 border-t border-[#1c2221] text-[11px] font-mono-tech text-[#59605F]">
              * Above telemetry values represent canonical runtime logging contracts specified in Project Masterplan §28.
            </div>
          </div>

          {/* Right Column: Key Explainability Pillars */}
          <div className="lg:col-span-5 space-y-6">
            
            <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg">
              <div className="flex items-center gap-3 mb-2 text-[#F5A623]">
                <FileText className="w-5 h-5" />
                <h3 className="font-heading font-bold text-lg text-[#F1F0EA]">Deterministic Replan Logging</h3>
              </div>
              <p className="text-sm text-[#8E9594] leading-relaxed">
                Every obstacle encounter outputs the precise pixel cluster, projected BEV coordinates, timestamp, and mathematical reason for route selection.
              </p>
            </div>

            <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg">
              <div className="flex items-center gap-3 mb-2 text-[#39FF88]">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-heading font-bold text-lg text-[#F1F0EA]">Clearance-Aware Buffers</h3>
              </div>
              <p className="text-sm text-[#8E9594] leading-relaxed">
                Rather than scraping hazard boundaries, paths enforce configurable metric clearance buffers (e.g. 0.6m to 1.0m) to guarantee chassis safety.
              </p>
            </div>

            <div className="p-5 bg-[#101313] border border-[#252A29] rounded-lg">
              <div className="flex items-center gap-3 mb-2 text-[#54D6FF]">
                <AlertTriangle className="w-5 h-5" />
                <h3 className="font-heading font-bold text-lg text-[#F1F0EA]">E-Stop & Safe Stop Trigger</h3>
              </div>
              <p className="text-sm text-[#8E9594] leading-relaxed">
                If all corridors are blocked or localization quality drops below safe thresholds, the system halts with an explicit operator diagnostic.
              </p>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
