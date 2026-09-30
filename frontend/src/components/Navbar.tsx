import React, { useState, useEffect } from 'react';
import { Compass, Cpu, ExternalLink, Activity, Terminal } from 'lucide-react';

interface NavbarProps {
  currentRoute: 'home' | 'prototype';
  onNavigate: (route: 'home' | 'prototype') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentRoute, onNavigate }) => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 border-b ${
        scrolled
          ? 'bg-[#080909]/90 backdrop-blur-md border-[#252A29]'
          : 'bg-[#080909]/40 backdrop-blur-sm border-[#1c2221]'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Tagline */}
        <div 
          onClick={() => onNavigate('home')} 
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-8 h-8 rounded border border-[#F5A623]/60 bg-[#151918] flex items-center justify-center relative overflow-hidden group-hover:border-[#F5A623] transition-colors">
            <Compass className="w-4 h-4 text-[#F5A623] animate-pulse" />
            <div className="absolute inset-0 bg-[#F5A623]/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-heading font-bold text-lg tracking-wider text-[#F1F0EA]">
                DRISHTI
              </span>
              <span className="font-mono-tech text-[10px] uppercase text-[#F5A623] px-1.5 py-0.5 bg-[#F5A623]/10 border border-[#F5A623]/30 rounded">
                v1.0
              </span>
            </div>
            <div className="font-mono-tech text-[9px] uppercase tracking-widest text-[#8E9594]">
              AUTONOMOUS VISION SYSTEM
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-8 font-mono-tech text-xs tracking-wider uppercase text-[#8E9594]">
          {currentRoute === 'home' ? (
            <>
              <a
                href="#system"
                className="hover:text-[#F5A623] transition-colors flex items-center gap-1.5"
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>SYSTEM</span>
              </a>
              <a
                href="#technology"
                className="hover:text-[#F5A623] transition-colors flex items-center gap-1.5"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>TECHNOLOGY</span>
              </a>
              <button
                onClick={() => onNavigate('prototype')}
                className="hover:text-[#54D6FF] transition-colors flex items-center gap-1.5"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>PROTOTYPE</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => onNavigate('home')}
              className="hover:text-[#F5A623] transition-colors"
            >
              ← BACK TO OVERVIEW
            </button>
          )}
        </nav>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 bg-[#101313] border border-[#252A29] rounded text-[10px] font-mono-tech text-[#8E9594]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#39FF88] animate-ping" />
            <span className="text-[#39FF88]">GPS: OFF</span>
          </div>

          {currentRoute === 'home' ? (
            <button
              onClick={() => onNavigate('prototype')}
              className="btn-primary py-2 px-4 text-xs font-mono-tech uppercase flex items-center gap-1.5"
            >
              <span>TEST THE PROTOTYPE</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={() => onNavigate('home')}
              className="btn-secondary py-2 px-3 text-xs font-mono-tech uppercase"
            >
              EXIT CONTROL
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
