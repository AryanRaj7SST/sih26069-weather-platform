import React from 'react';

export const MapHeaderCard: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-md p-4 sm:p-5 shadow-lg max-w-lg">
      <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
        Live Weather Event Map
      </h1>
      <p className="mt-1 text-xs sm:text-sm text-slate-600 leading-relaxed">
        Explore reported weather incidents across the Indian subcontinent.
      </p>
    </div>
  );
};
