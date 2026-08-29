import React from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { CitizenReportForm } from '@/features/reports/CitizenReportForm';

export const CitizenReportPage: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50/50 text-slate-900">
      {/* Navigation Header */}
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 py-8 sm:py-12">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          {/* Page Heading matching Stitch Reference */}
          <div className="text-center mb-8 sm:mb-10">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              Report Weather Event
            </h1>
            <p className="mt-3 text-sm sm:text-base leading-relaxed text-slate-600 max-w-2xl mx-auto">
              Your accurate reports help improve weather forecasting and enhance public safety in your community.
            </p>
          </div>

          {/* Citizen Reporting Form */}
          <CitizenReportForm />
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};
