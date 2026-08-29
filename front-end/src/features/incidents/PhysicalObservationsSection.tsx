// Physical Observations (IMD AWS & CWC Gauge) Corroboration Section

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Radio, CloudRain, Wind, Waves, MapPin, ChevronLeft, ChevronRight } from 'lucide-react';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { formatDateTime, formatObservationRelationship } from '@/lib/presentation';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';

interface PhysicalObservationsSectionProps {
  incidentId: string;
  totalCount?: number;
}

export const PhysicalObservationsSection: React.FC<PhysicalObservationsSectionProps> = ({
  incidentId,
  totalCount,
}) => {
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const { data: response, isLoading, isError, error, refetch } = useQuery({
    queryKey: incidentKeys.observations(incidentId, page),
    queryFn: ({ signal }) => incidentApi.getIncidentObservations(incidentId, page, pageSize, signal),
    staleTime: 1000 * 60, // 1 minute
  });

  const observations = response?.data || [];
  const pagination = response?.pagination;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <Radio className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              Physical Meteorological Observations
            </h3>
            <span className="text-[11px] text-slate-400 font-medium block">
              Official IMD AWS and CWC sensor gauge readings in proximity
            </span>
          </div>
        </div>

        {totalCount !== undefined && (
          <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
            {totalCount} {totalCount === 1 ? 'Reading' : 'Readings'}
          </span>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton count={2} className="h-24" />
      ) : isError ? (
        <ErrorCard
          title="Observation Readings Unavailable"
          message={error instanceof Error ? error.message : 'Unable to retrieve station observation data.'}
          onRetry={() => refetch()}
        />
      ) : observations.length === 0 ? (
        <EmptyState
          title="No Sensor Readings in Proximity"
          description="No official IMD automatic weather stations or CWC gauges were in range during this event window."
        />
      ) : (
        <div className="space-y-3 pt-3 border-t border-slate-100">
          <div className="space-y-3">
            {observations.map((item) => {
              const relStyle = formatObservationRelationship(item.relationship);

              return (
                <div
                  key={item.corroboration_id || item.observation_id}
                  className="rounded-xl border border-slate-200/80 bg-slate-50/40 p-3.5 space-y-2 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center space-x-1 text-[11px] font-bold text-slate-800 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                        <span>{item.station_name || item.station_code || 'Automatic Weather Station'}</span>
                        {item.station_code && (
                          <span className="text-slate-400 font-mono text-[9px]">({item.station_code})</span>
                        )}
                      </span>
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold border ${relStyle.badgeClass}`}
                      >
                        {relStyle.label}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-[10px] text-slate-500 font-medium">
                      {item.distance_km != null && (
                        <span className="flex items-center space-x-1">
                          <MapPin className="h-3 w-3 text-blue-600" aria-hidden="true" />
                          <span>{item.distance_km.toFixed(1)} km away</span>
                        </span>
                      )}
                      <span className="bg-slate-200/80 px-1.5 py-0.5 rounded text-slate-700 font-mono">
                        {item.source_code}
                      </span>
                    </div>
                  </div>

                  {/* Metrics Badges */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    {item.metrics.rainfall_mm != null && (
                      <div className="rounded-lg bg-white border border-slate-200/80 p-2 flex items-center space-x-2">
                        <CloudRain className="h-4 w-4 text-blue-600 shrink-0" aria-hidden="true" />
                        <div>
                          <span className="text-[9px] text-slate-400 font-extrabold uppercase block">Rainfall</span>
                          <span className="text-xs font-extrabold text-slate-900">{item.metrics.rainfall_mm} mm</span>
                        </div>
                      </div>
                    )}

                    {item.metrics.water_level_m != null && (
                      <div className="rounded-lg bg-white border border-slate-200/80 p-2 flex items-center space-x-2">
                        <Waves className="h-4 w-4 text-sky-600 shrink-0" aria-hidden="true" />
                        <div>
                          <span className="text-[9px] text-slate-400 font-extrabold uppercase block">Water Level</span>
                          <span className="text-xs font-extrabold text-slate-900">{item.metrics.water_level_m} m</span>
                        </div>
                      </div>
                    )}

                    {item.metrics.wind_speed_kmh != null && (
                      <div className="rounded-lg bg-white border border-slate-200/80 p-2 flex items-center space-x-2">
                        <Wind className="h-4 w-4 text-indigo-600 shrink-0" aria-hidden="true" />
                        <div>
                          <span className="text-[9px] text-slate-400 font-extrabold uppercase block">Wind Speed</span>
                          <span className="text-xs font-extrabold text-slate-900">{item.metrics.wind_speed_kmh} km/h</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-200/40">
                    <span>Observed: {formatDateTime(item.observed_at)}</span>
                    <span className="font-mono text-[9px] text-slate-400">
                      Corroboration Factor: {(item.corroboration_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
              <span className="text-slate-500 font-medium">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <div className="flex items-center space-x-1.5">
                <button
                  type="button"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-slate-200 px-2.5 py-1 font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded-lg border border-slate-200 px-2.5 py-1 font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
