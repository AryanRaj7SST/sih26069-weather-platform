import React from 'react';
import { CitizenReportForm } from '@/features/reports/CitizenReportForm';

export const CitizenReportPage: React.FC = () => {
  return (
    <div className="py-8 sm:py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8 sm:mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Report Weather Event
          </h1>
          <p className="mt-3 text-sm sm:text-base leading-relaxed text-slate-600 max-w-2xl mx-auto">
            Your accurate reports help improve weather forecasting and enhance public safety in your community.
          </p>
        </div>

        <CitizenReportForm />
      </div>
    </div>
  );
};
