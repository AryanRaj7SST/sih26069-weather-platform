import React from 'react';
import { MapPin } from 'lucide-react';
import { LocationDetail } from '@/types';

interface LocationCardProps {
  location: LocationDetail;
}

export const LocationCard: React.FC<LocationCardProps> = ({ location }) => {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center space-x-2 text-slate-500">
        <MapPin className="h-4 w-4 text-blue-600" />
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Location
        </span>
      </div>

      <p className="mt-2 text-base font-bold text-slate-900">
        {location.name || 'Reported Incident Locality'}
      </p>

      <p className="mt-1 font-mono text-xs text-slate-500">
        Lat: {location.latitude.toFixed(4)}° N, Lon: {location.longitude.toFixed(4)}° E
      </p>

      {/* Visual Map Area */}
      <div className="relative mt-4 h-32 overflow-hidden rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center">
        <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:14px_14px] opacity-70" />
        <div className="relative z-10 flex flex-col items-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white shadow-md">
            <MapPin className="h-5 w-5" />
          </div>
          <span className="mt-1.5 rounded bg-white/95 px-2 py-0.5 font-mono text-[10px] font-semibold text-slate-700 shadow-sm border border-slate-200">
            {location.latitude.toFixed(4)}°, {location.longitude.toFixed(4)}°
          </span>
        </div>
      </div>
    </div>
  );
};
