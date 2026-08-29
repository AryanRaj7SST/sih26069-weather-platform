import React from 'react';
import { MapPin, Plus, Minus, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export const LiveEventMapPreview: React.FC = () => {
  return (
    <div id="live-map-overview" className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <MapPin className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-bold text-slate-900">Live Event Map</h2>
        </div>
        <Link
          to="/report"
          className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
        >
          <span>View Full Screen</span>
          <ExternalLink className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Map visual canvas matching Stitch */}
      <div className="relative mt-4 h-72 md:h-80 w-full overflow-hidden rounded-xl border border-slate-200 bg-emerald-50/40">
        {/* Abstract topographic / grid styling */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:28px_28px] opacity-60" />

        {/* Coastal terrain & landmark accents */}
        <div className="absolute top-1/4 left-1/3 h-28 w-44 rounded-full bg-teal-100/60 blur-xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 h-32 w-52 rounded-full bg-sky-100/70 blur-xl pointer-events-none" />

        {/* Observation Markers */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center">
          <span className="relative flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-4 w-4 bg-rose-600 border-2 border-white shadow-sm" />
          </span>
          <span className="mt-1 rounded bg-white/90 px-1.5 py-0.5 text-[9px] font-bold text-slate-800 shadow-sm border border-slate-200">
            Mumbai Watch
          </span>
        </div>

        <div className="absolute top-1/2 left-1/4 flex flex-col items-center">
          <span className="relative flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-amber-500 border-2 border-white shadow-sm" />
          </span>
        </div>

        <div className="absolute bottom-1/3 right-1/3 flex flex-col items-center">
          <span className="relative flex h-3.5 w-3.5">
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-600 border-2 border-white shadow-sm" />
          </span>
          <span className="mt-1 rounded bg-white/90 px-1.5 py-0.5 text-[9px] font-bold text-slate-800 shadow-sm border border-slate-200">
            Chennai Flood
          </span>
        </div>

        {/* Live Status Pill */}
        <div className="absolute top-3 left-3 flex items-center space-x-1.5 rounded-full bg-white/95 px-2.5 py-1 text-[11px] font-bold text-slate-700 shadow-sm border border-slate-200">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>LIVE: 14:05 IST</span>
        </div>

        {/* Map Zoom Controls */}
        <div className="absolute bottom-3 right-3 flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <button
            type="button"
            className="flex h-7 w-7 items-center justify-center border-b border-slate-200 text-slate-600 hover:bg-slate-50"
            aria-label="Zoom in"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="flex h-7 w-7 items-center justify-center text-slate-600 hover:bg-slate-50"
            aria-label="Zoom out"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
