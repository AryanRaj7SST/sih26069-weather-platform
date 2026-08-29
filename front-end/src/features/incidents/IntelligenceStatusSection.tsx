// Intelligence Pipeline Orchestration Status Section

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Cpu } from 'lucide-react';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { IncidentIntelligenceSummary, StageName } from '@/types';
import { formatReadiness, formatStageOutcome } from '@/lib/presentation';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { ErrorCard } from '@/components/common/ErrorCard';

interface IntelligenceStatusSectionProps {
  incidentId: string;
  initialSummary?: IncidentIntelligenceSummary;
}

const STAGES: { key: StageName; label: string; description: string }[] = [
  { key: 'LOCATION', label: 'Entity & Location Resolution', description: 'Geocoding and administrative boundary alignment' },
  { key: 'DUPLICATE', label: 'Duplicate Clustering', description: 'Semantic clustering against active incident reports' },
  { key: 'EVIDENCE', label: 'Digital Evidence Linking', description: 'GDELT and news broadcast corroboration' },
  { key: 'OBSERVATION', label: 'Physical Observation', description: 'IMD AWS and CWC gauge telemetry alignment' },
  { key: 'CREDIBILITY', label: 'Credibility Scoring', description: 'Explainable machine-assessed credibility scoring' },
];

export const IntelligenceStatusSection: React.FC<IntelligenceStatusSectionProps> = ({
  incidentId,
  initialSummary,
}) => {
  const { data: response, isLoading, isError, error, refetch } = useQuery({
    queryKey: incidentKeys.intelligence(incidentId),
    queryFn: ({ signal }) => incidentApi.getIncidentIntelligence(incidentId, signal),
    staleTime: 1000 * 30, // 30 seconds
  });

  const intelligence = response?.data;
  const readiness = intelligence?.overall_readiness || initialSummary?.overall_readiness;
  const readinessStyle = formatReadiness(readiness);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <Cpu className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              Intelligence Orchestration Pipeline
            </h3>
            <span className="text-[11px] text-slate-400 font-medium block">
              Multi-stage deterministic enrichment and automated corroboration workflow
            </span>
          </div>
        </div>

        <span
          className={`inline-flex items-center space-x-1.5 rounded-full px-3 py-1 text-xs font-bold border ${readinessStyle.badgeClass}`}
        >
          <span className={`h-2 w-2 rounded-full ${readinessStyle.pillBg}`} aria-hidden="true" />
          <span>{readinessStyle.label}</span>
        </span>
      </div>

      {isLoading ? (
        <LoadingSkeleton count={3} className="h-16" />
      ) : isError ? (
        <ErrorCard
          title="Pipeline Telemetry Unavailable"
          message={error instanceof Error ? error.message : 'Unable to retrieve stage execution status.'}
          onRetry={() => refetch()}
        />
      ) : (
        <div className="space-y-3 pt-3 border-t border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {STAGES.map((stage) => {
              const stageData = intelligence?.stages?.[stage.key];
              const outcome = stageData?.status;
              const outcomeStyle = formatStageOutcome(outcome);

              return (
                <div
                  key={stage.key}
                  className="rounded-xl border border-slate-100 bg-slate-50/60 p-3 flex flex-col justify-between space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{stage.label}</h4>
                      <p className="text-[10px] text-slate-500 line-clamp-1">{stage.description}</p>
                    </div>

                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold border shrink-0 ${outcomeStyle.badgeClass}`}
                    >
                      {outcomeStyle.label}
                    </span>
                  </div>

                  {stageData && (
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono border-t border-slate-200/50 pt-1.5">
                      <span>Attempt #{stageData.attempt}</span>
                      {stageData.duration_ms != null && <span>{stageData.duration_ms.toFixed(1)} ms</span>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
