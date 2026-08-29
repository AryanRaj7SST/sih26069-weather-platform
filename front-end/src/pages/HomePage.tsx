import React from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { HeroSection } from '@/features/home/HeroSection';
import { ActiveAdvisoriesCard } from '@/features/home/ActiveAdvisoriesCard';
import { LiveEventMapPreview } from '@/features/home/LiveEventMapPreview';
import { ProcessFlowCard } from '@/features/home/ProcessFlowCard';
import { RecentReportsTable } from '@/features/home/RecentReportsTable';

export const HomePage: React.FC = () => {
  const handleScrollToMap = () => {
    const mapElement = document.getElementById('live-map-overview');
    if (mapElement) {
      mapElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50/60 text-slate-900 pb-16 md:pb-0">
      {/* Navigation Header */}
      <Navbar />

      {/* Main Content */}
      <main className="flex-1">
        {/* Hero Section matching Stitch */}
        <HeroSection onExploreMapClick={handleScrollToMap} />

        {/* Content Section */}
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
          {/* Top Section: Active Advisories & Live Event Map */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ActiveAdvisoriesCard />
            <LiveEventMapPreview />
          </div>

          {/* Bottom Section: Processing Flow & Recent Verified Reports */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ProcessFlowCard />
            <RecentReportsTable />
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />

      {/* Mobile Sticky Bottom Navigation matching Stitch Mobile */}
      <MobileBottomNav />
    </div>
  );
};
