import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './sections/Hero';
import { Problem } from './sections/Problem';
import { Pipeline } from './sections/Pipeline';
import { Intelligence } from './sections/Intelligence';
import { CostmapVisualizer } from './sections/CostmapVisualizer';
import { Explainability } from './sections/Explainability';
import { Confidence } from './sections/Confidence';
import { Technology } from './sections/Technology';
import { PrototypeCTA } from './sections/PrototypeCTA';
import { Roadmap } from './sections/Roadmap';
import { Footer } from './components/Footer';
import { PrototypePage } from './pages/PrototypePage';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<'home' | 'prototype'>('home');

  // Handle URL hash or direct routing
  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname === '/prototype' || window.location.hash === '#prototype') {
        setCurrentRoute('prototype');
      } else {
        setCurrentRoute('home');
      }
    };

    handlePopState();
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);

  const navigateTo = (route: 'home' | 'prototype') => {
    setCurrentRoute(route);
    if (route === 'prototype') {
      window.history.pushState(null, '', '#prototype');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      window.history.pushState(null, '', '#');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const scrollToSystem = () => {
    const systemEl = document.getElementById('problem');
    if (systemEl) {
      systemEl.scrollIntoView({ behavior: 'smooth' });
    }
  };

  if (currentRoute === 'prototype') {
    return <PrototypePage onBackToHome={() => navigateTo('home')} />;
  }

  return (
    <div className="min-h-screen bg-[#080909] text-[#F1F0EA] flex flex-col">
      {/* 01 Navigation */}
      <Navbar currentRoute={currentRoute} onNavigate={navigateTo} />

      {/* Main Landing Page Content */}
      <main className="flex-1">
        {/* 02 Hero */}
        <Hero
          onExploreSystem={scrollToSystem}
          onOpenPrototype={() => navigateTo('prototype')}
        />

        {/* 03 Problem */}
        <Problem />

        {/* 04 System Pipeline */}
        <Pipeline />

        {/* 05 Intelligence */}
        <Intelligence />

        {/* 06 Costmap Visualization */}
        <CostmapVisualizer />

        {/* 07 Explainability */}
        <Explainability />

        {/* 08 Confidence */}
        <Confidence />

        {/* 09 Technology */}
        <Technology />

        {/* 10 Prototype CTA */}
        <PrototypeCTA onOpenPrototype={() => navigateTo('prototype')} />

        {/* 11 Roadmap */}
        <Roadmap />
      </main>

      {/* 12 Footer */}
      <Footer
        onOpenPrototype={() => navigateTo('prototype')}
        onNavigateHome={() => navigateTo('home')}
      />
    </div>
  );
};

export default App;
