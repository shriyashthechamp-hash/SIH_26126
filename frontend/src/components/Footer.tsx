import React from 'react';
import { Compass, Github, ExternalLink } from 'lucide-react';

interface FooterProps {
  onOpenPrototype: () => void;
  onNavigateHome: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenPrototype, onNavigateHome }) => {
  return (
    <footer className="bg-[#080909] border-t border-[#252A29] py-16 text-[#8E9594] font-mono-tech text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 pb-12 border-b border-[#1c2221]">
          
          {/* Brand Col */}
          <div className="space-y-4 md:col-span-2">
            <div 
              onClick={onNavigateHome}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-8 h-8 rounded border border-[#F5A623]/60 bg-[#151918] flex items-center justify-center group-hover:border-[#F5A623] transition-colors">
                <Compass className="w-4 h-4 text-[#F5A623]" />
              </div>
              <span className="font-heading font-bold text-xl text-[#F1F0EA]">
                DRISHTI
              </span>
            </div>
            <p className="text-sm text-[#8E9594] max-w-md font-normal leading-relaxed">
              Vision-based autonomous navigation for unmanned ground vehicles in GPS-denied environments. Developed under SIH 26126.
            </p>
            <div className="flex items-center gap-4 text-[#59605F] text-[11px]">
              <span>SIH PROBLEM ID: 26126</span>
              <span>•</span>
              <span className="text-[#39FF88]">CAMERA-FIRST AUTONOMY</span>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="space-y-3">
            <div className="text-[#F1F0EA] font-bold uppercase tracking-wider text-[11px]">
              SYSTEM ARCHITECTURE
            </div>
            <ul className="space-y-2">
              <li>
                <a href="#system" className="hover:text-[#F5A623] transition-colors">
                  System Pipeline
                </a>
              </li>
              <li>
                <a href="#intelligence" className="hover:text-[#F5A623] transition-colors">
                  Perception & Reasoning
                </a>
              </li>
              <li>
                <a href="#costmap" className="hover:text-[#F5A623] transition-colors">
                  Traversability Costmap
                </a>
              </li>
              <li>
                <a href="#explainability" className="hover:text-[#F5A623] transition-colors">
                  Explainable Telemetry
                </a>
              </li>
              <li>
                <a href="#technology" className="hover:text-[#F5A623] transition-colors">
                  Technology Stack
                </a>
              </li>
            </ul>
          </div>

          {/* Prototype & Code */}
          <div className="space-y-3">
            <div className="text-[#F1F0EA] font-bold uppercase tracking-wider text-[11px]">
              PROTOTYPE & REPO
            </div>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={onOpenPrototype}
                  className="hover:text-[#F5A623] text-left transition-colors flex items-center gap-1.5"
                >
                  <span>Mission Control Simulator</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </li>
              <li>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-[#F5A623] transition-colors flex items-center gap-1.5"
                >
                  <Github className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </a>
              </li>
              <li>
                <a href="#roadmap" className="hover:text-[#F5A623] transition-colors">
                  Engineering Roadmap
                </a>
              </li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-[#59605F]">
          <div>
            © {new Date().getFullYear()} DRISHTI Project — SIH 26126. All rights reserved.
          </div>
          <div className="flex items-center gap-3">
            <span>STATIC DEPLOYMENT (VITE/VERCEL)</span>
            <span>•</span>
            <span className="text-[#F5A623]">DEMO MODE</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
