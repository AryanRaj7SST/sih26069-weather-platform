import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { CitizenNavbar } from './CitizenNavbar';
import { Footer } from './Footer';
import { CitizenBottomNav } from './CitizenBottomNav';
import { PageFallback } from '@/components/common/PageFallback';

export const CitizenLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased pb-16 md:pb-0">
      <CitizenNavbar />
      <main className="flex-1">
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <CitizenBottomNav />
    </div>
  );
};
