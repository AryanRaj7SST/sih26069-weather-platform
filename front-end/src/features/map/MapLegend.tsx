import React from 'react';

export const MapLegend: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/95 backdrop-blur-md p-3.5 shadow-lg">
      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
        Legend
      </h3>
      <div className="space-y-2 text-xs">
        <div className="flex items-center space-x-2.5">
          <span className="h-3.5 w-3.5 rounded-full bg-rose-600 border-2 border-white shadow-sm shrink-0" />
          <span className="font-semibold text-slate-700">Severe Event (Single)</span>
        </div>
        <div className="flex items-center space-x-2.5">
          <span className="h-3.5 w-3.5 rounded-full bg-emerald-600 border-2 border-white shadow-sm shrink-0" />
          <span className="font-semibold text-slate-700">Moderate Event (Single)</span>
        </div>
        <div className="flex items-center space-x-2.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-600 text-white text-[10px] font-bold border-2 border-white shadow-sm shrink-0">
            N
          </span>
          <span className="font-semibold text-slate-700">Incident Cluster (Location)</span>
        </div>
      </div>
    </div>
  );
};
