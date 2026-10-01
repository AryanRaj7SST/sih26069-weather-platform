import React from 'react';
import { HeroSection } from '@/features/home/HeroSection';
import { ActiveAdvisoriesCard } from '@/features/home/ActiveAdvisoriesCard';
import { LiveEventMapPreview } from '@/features/home/LiveEventMapPreview';
import { ProcessFlowCard } from '@/features/home/ProcessFlowCard';
import { RecentReportsTable } from '@/features/home/RecentReportsTable';

export const HomePage: React.FC = () => {
  return (
    <div className="py-6">
      <HeroSection />

      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ActiveAdvisoriesCard />
          <LiveEventMapPreview />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ProcessFlowCard />
          <RecentReportsTable />
        </div>
      </div>
    </div>
  );
};
