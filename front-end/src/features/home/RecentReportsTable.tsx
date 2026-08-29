import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CloudRain, Droplets, Wind, AlertTriangle, Sun, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { formatHazardCategory, formatRelativeTime } from '@/lib/presentation';
import { IncidentSummary } from '@/types';

export const RecentReportsTable: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: incidentKeys.list({ verification_status: 'VERIFIED', page_size: 5 }),
    queryFn: () =>
      incidentApi.listIncidents({
        verification_status: 'VERIFIED',
        page: 1,
        page_size: 5,
      }),
    staleTime: 1000 * 60 * 2,
  });

  const reports: IncidentSummary[] = data?.data || [];

  const getHazardIcon = (categoryCode?: string) => {
    const clean = (categoryCode || '').toUpperCase();
    if (clean.includes('FLOOD') || clean.includes('WATERLOGGING')) {
      return <Droplets className="h-4 w-4 text-blue-600 shrink-0" />;
    }
    if (clean.includes('RAIN')) {
      return <CloudRain className="h-4 w-4 text-sky-600 shrink-0" />;
    }
    if (clean.includes('WIND') || clean.includes('CYCLONE') || clean.includes('STORM')) {
      return <Wind className="h-4 w-4 text-teal-600 shrink-0" />;
    }
    if (clean.includes('LANDSLIDE')) {
      return <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />;
    }
    if (clean.includes('HEAT')) {
      return <Sun className="h-4 w-4 text-orange-600 shrink-0" />;
    }
    return <CloudRain className="h-4 w-4 text-slate-600 shrink-0" />;
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Recent Verified Reports</h2>
            <p className="text-xs text-slate-500 mt-0.5">Authoritative ground truth confirmed by emergency operators</p>
          </div>
          <Link
            to="/incidents?verification_status=VERIFIED"
            className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
          >
            <span>View All</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>

        {isLoading && (
          <div className="mt-4 space-y-3 py-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between py-2.5 animate-pulse">
                <div className="flex items-center space-x-2">
                  <div className="h-4 w-4 rounded bg-slate-200" />
                  <div className="h-3.5 w-24 rounded bg-slate-200" />
                </div>
                <div className="h-3.5 w-32 rounded bg-slate-200" />
                <div className="h-3.5 w-12 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-center text-xs text-amber-800">
            <p className="font-semibold">Unable to fetch live verified reports.</p>
            <p className="text-[11px] text-amber-700 mt-0.5">Please check network connection or backend services.</p>
          </div>
        )}

        {!isLoading && !isError && reports.length === 0 && (
          <div className="mt-6 py-8 text-center text-xs text-slate-500">
            <p className="font-semibold text-slate-700">No verified reports recorded yet.</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Reports will appear here once confirmed through the operator verification queue.
            </p>
          </div>
        )}

        {!isLoading && !isError && reports.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="pb-2.5 font-medium">Type</th>
                  <th className="pb-2.5 font-medium">Location</th>
                  <th className="pb-2.5 font-medium text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reports.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="py-3">
                      <Link
                        to={`/incidents/${item.id}`}
                        className="flex items-center space-x-2 font-semibold text-slate-800 group-hover:text-blue-600 transition-colors"
                      >
                        {getHazardIcon(item.category?.code)}
                        <span className="truncate max-w-[140px] sm:max-w-[180px]">
                          {item.title || formatHazardCategory(item.category?.code)}
                        </span>
                      </Link>
                    </td>
                    <td className="py-3 text-slate-600 font-medium truncate max-w-[120px] sm:max-w-[180px]">
                      {item.location?.name || 'Geotagged Location'}
                    </td>
                    <td className="py-3 text-right font-mono text-slate-500 whitespace-nowrap">
                      {formatRelativeTime(item.occurred_at || item.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span className="font-medium">Track your personal submission?</span>
        <Link
          to="/track-report"
          className="font-bold text-blue-600 hover:text-blue-700 transition-colors"
        >
          Track by ID &rarr;
        </Link>
      </div>
    </div>
  );
};
