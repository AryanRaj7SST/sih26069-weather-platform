import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { IncidentSummary } from '@/types';

export const ActiveAdvisoriesCard: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: incidentKeys.list({
      verification_status: 'PENDING,UNDER_REVIEW,VERIFIED',
      page_size: 4,
    }),
    queryFn: () =>
      incidentApi.listIncidents({
        verification_status: 'PENDING,UNDER_REVIEW,VERIFIED',
        page: 1,
        page_size: 4,
      }),
    staleTime: 1000 * 60 * 2,
  });

  const incidents: IncidentSummary[] = data?.data || [];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-5 w-5 text-rose-500" />
            <div>
              <h2 className="text-lg font-bold text-slate-900">Active Advisory Summary</h2>
              <p className="text-xs text-slate-500 mt-0.5">High-priority regional meteorological events</p>
            </div>
          </div>
          <Link
            to="/incidents"
            className="inline-flex items-center space-x-1 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <span>Live Telemetry</span>
            <ArrowUpRight className="h-3 w-3 text-slate-500" />
          </Link>
        </div>

        {isLoading && (
          <div className="mt-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 animate-pulse space-y-3">
                <div className="flex justify-between items-start">
                  <div className="space-y-1.5">
                    <div className="h-4 w-40 rounded bg-slate-200" />
                    <div className="h-3 w-28 rounded bg-slate-200" />
                  </div>
                  <div className="h-5 w-16 rounded bg-slate-200" />
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <div className="h-3 w-20 rounded bg-slate-200" />
                    <div className="h-3 w-10 rounded bg-slate-200" />
                  </div>
                  <div className="h-1.5 w-full rounded bg-slate-200" />
                </div>
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50/70 p-4 text-center text-xs text-rose-800">
            <p className="font-semibold">Unable to fetch active advisories.</p>
            <p className="text-[11px] text-rose-700 mt-0.5">Check backend API connection or refresh the page.</p>
          </div>
        )}

        {!isLoading && !isError && incidents.length === 0 && (
          <div className="mt-6 py-8 text-center text-xs text-slate-500">
            <p className="font-semibold text-slate-700">No active severe advisories at this time.</p>
            <p className="text-[11px] text-slate-400 mt-1">
              Active incident alerts and severe weather warnings will appear here in real time.
            </p>
          </div>
        )}

        {!isLoading && !isError && incidents.length > 0 && (
          <div className="mt-4 space-y-3">
            {incidents.map((item) => {
              const isSevere = item.severity === 'SEVERE';
              const isHigh = item.severity === 'HIGH';
              const isPendingAssessment =
                item.credibility_score == null ||
                item.credibility_score === 0 ||
                item.readiness === 'INTELLIGENCE_PENDING';
              const credScorePct =
                item.credibility_score != null ? Math.round(item.credibility_score * 100) : null;

              return (
                <Link
                  key={item.id}
                  to={`/incidents/${item.id}`}
                  className="block rounded-xl border border-slate-100 bg-slate-50/60 p-3.5 transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-xs group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center space-x-1.5">
                        {isSevere && <AlertTriangle className="h-3.5 w-3.5 text-rose-600 shrink-0" />}
                        <h3 className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                          {item.title}
                        </h3>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">
                        {item.location?.name || 'Geotagged Incident'}
                      </p>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                        isSevere
                          ? 'bg-rose-100 text-rose-700 border border-rose-200'
                          : isHigh
                          ? 'bg-orange-100 text-orange-700 border border-orange-200'
                          : 'bg-amber-100 text-amber-700 border border-amber-200'
                      }`}
                    >
                      {item.severity}
                    </span>
                  </div>

                  {/* Real Machine Credibility Metric */}
                  <div className="mt-2.5">
                    <div className="flex justify-between items-center text-[10px] font-semibold text-slate-600">
                      <span>Machine Credibility</span>
                      {isPendingAssessment ? (
                        <span className="font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200/60 text-[9px]">
                          Pending Assessment
                        </span>
                      ) : (
                        <span className="font-mono text-slate-800">{credScorePct}%</span>
                      )}
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                      {isPendingAssessment ? (
                        <div className="h-full rounded-full bg-amber-400/80 animate-pulse w-2/3" />
                      ) : (
                        <div
                          className={`h-full rounded-full transition-all ${
                            isSevere ? 'bg-rose-500' : isHigh ? 'bg-orange-500' : 'bg-blue-600'
                          }`}
                          style={{ width: `${Math.max(5, Math.min(100, credScorePct ?? 0))}%` }}
                        />
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span>Need full situational awareness?</span>
        <Link
          to="/incidents"
          className="font-bold text-blue-600 hover:text-blue-700 transition-colors"
        >
          Incident Explorer &rarr;
        </Link>
      </div>
    </div>
  );
};
