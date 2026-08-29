import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin, ExternalLink, Layers } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';

export const LiveEventMapPreview: React.FC = () => {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: incidentKeys.list({ page_size: 1 }),
    queryFn: () => incidentApi.listIncidents({ page: 1, page_size: 1 }),
    staleTime: 1000 * 60 * 2,
  });

  const totalEvents = data?.pagination?.total_records ?? 0;

  return (
    <div id="live-map-overview" className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <MapPin className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-lg font-bold text-slate-900">Live Geospatial Map</h2>
              <p className="text-xs text-slate-500 mt-0.5">National real-time weather & hazard tracking</p>
            </div>
          </div>
          <Link
            to="/live-map"
            className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
          >
            <span>View Full Screen</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* Map visual canvas linking to full screen interactive map */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => navigate('/live-map')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              navigate('/live-map');
            }
          }}
          className="relative mt-4 h-72 md:h-80 w-full overflow-hidden rounded-xl border border-slate-200 bg-emerald-50/40 cursor-pointer group transition-all hover:border-blue-400 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Click to open interactive live map"
        >
          {/* Abstract topographic / grid styling */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:28px_28px] opacity-60" />

          {/* Coastal terrain & landmark accents */}
          <div className="absolute top-1/4 left-1/3 h-28 w-44 rounded-full bg-teal-100/60 blur-xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-1/4 h-32 w-52 rounded-full bg-sky-100/70 blur-xl pointer-events-none" />

          {/* Dynamic Pin Accents */}
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group-hover:scale-110 transition-transform">
            <span className="relative flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-4 w-4 bg-rose-600 border-2 border-white shadow-sm" />
            </span>
            <span className="mt-1 rounded bg-white/95 px-1.5 py-0.5 text-[9px] font-bold text-slate-800 shadow-sm border border-slate-200">
              Active Focus
            </span>
          </div>

          <div className="absolute top-1/2 left-1/4 flex flex-col items-center group-hover:scale-110 transition-transform">
            <span className="relative flex h-3.5 w-3.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-amber-500 border-2 border-white shadow-sm" />
            </span>
          </div>

          <div className="absolute bottom-1/3 right-1/3 flex flex-col items-center group-hover:scale-110 transition-transform">
            <span className="relative flex h-3.5 w-3.5">
              <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-600 border-2 border-white shadow-sm" />
            </span>
            <span className="mt-1 rounded bg-white/95 px-1.5 py-0.5 text-[9px] font-bold text-slate-800 shadow-sm border border-slate-200">
              Verified Pin
            </span>
          </div>

          {/* Live Status Pill with Backend-Backed Count */}
          <div className="absolute top-3 left-3 flex items-center space-x-1.5 rounded-full bg-white/95 px-3 py-1 text-[11px] font-bold text-slate-800 shadow-md border border-slate-200">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <span>
              {isLoading ? 'SYNCING...' : `LIVE: ${totalEvents} Incident${totalEvents === 1 ? '' : 's'} Tracked`}
            </span>
          </div>

          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-blue-900/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <div className="rounded-xl bg-white/95 px-4 py-2 text-xs font-bold text-blue-700 shadow-lg border border-blue-200 flex items-center space-x-2">
              <Layers className="h-4 w-4" />
              <span>Launch Interactive Leaflet GIS</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span>Includes radar, river gauges & citizen clusters</span>
        <Link
          to="/live-map"
          className="font-bold text-blue-600 hover:text-blue-700 transition-colors"
        >
          Open Live Map &rarr;
        </Link>
      </div>
    </div>
  );
};
