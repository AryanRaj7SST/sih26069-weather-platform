// Machine Credibility Assessment Section

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, TrendingUp, TrendingDown, HelpCircle } from 'lucide-react';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { IncidentCredibilitySummary } from '@/types';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { ErrorCard } from '@/components/common/ErrorCard';

interface CredibilitySectionProps {
  incidentId: string;
  initialSummary?: IncidentCredibilitySummary;
}

export const CredibilitySection: React.FC<CredibilitySectionProps> = ({
  incidentId,
  initialSummary,
}) => {
  const { data: response, isLoading, isError, error, refetch } = useQuery({
    queryKey: incidentKeys.credibility(incidentId),
    queryFn: ({ signal }) => incidentApi.getIncidentCredibility(incidentId, signal),
    staleTime: 1000 * 60, // 1 minute
  });

  const credibility = response?.data;
  const scoreValue = credibility
    ? Math.round(credibility.score * 100)
    : initialSummary?.score != null
    ? Math.round(initialSummary.score * 100)
    : null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              Machine-Assessed Credibility
            </h3>
            <span className="text-[11px] text-slate-400 font-medium block">
              Statistical baseline derived from multi-source physical and digital signals
            </span>
          </div>
        </div>

        {scoreValue != null && (
          <div className="text-right">
            <div className="flex items-baseline space-x-1 justify-end">
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                {scoreValue}
              </span>
              <span className="text-xs font-bold text-slate-400">/ 100</span>
            </div>
            <span className="text-[10px] font-bold text-indigo-600 block -mt-0.5 uppercase tracking-wider">
              {credibility?.label || initialSummary?.label || 'Machine Assessed'}
            </span>
          </div>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton count={2} className="h-20" />
      ) : isError ? (
        <ErrorCard
          title="Credibility Signals Unavailable"
          message={error instanceof Error ? error.message : 'Unable to fetch credibility explanation.'}
          onRetry={() => refetch()}
        />
      ) : credibility ? (
        <div className="space-y-4 pt-3 border-t border-slate-100 text-xs">
          {/* Explanation Text */}
          {credibility.explanation_text && (
            <div className="rounded-xl border border-indigo-100/80 bg-indigo-50/40 p-3.5 text-indigo-950 leading-relaxed font-medium">
              {credibility.explanation_text}
            </div>
          )}

          {/* Positive Drivers */}
          {credibility.positive_drivers && credibility.positive_drivers.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
                <TrendingUp className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
                <span>Supporting Drivers</span>
              </h4>
              <ul className="space-y-1.5 pl-1">
                {credibility.positive_drivers.map((driver, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-slate-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" aria-hidden="true" />
                    <span>{driver}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Negative Drivers */}
          {credibility.negative_drivers && credibility.negative_drivers.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
                <TrendingDown className="h-3.5 w-3.5 text-rose-600" aria-hidden="true" />
                <span>Contradicting / Penalizing Factors</span>
              </h4>
              <ul className="space-y-1.5 pl-1">
                {credibility.negative_drivers.map((driver, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-rose-900">
                    <span className="h-1.5 w-1.5 rounded-full bg-rose-500 mt-1.5 shrink-0" aria-hidden="true" />
                    <span>{driver}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Uncertainty Flags */}
          {credibility.uncertainty_flags && credibility.uncertainty_flags.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
                <HelpCircle className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                <span>Uncertainty & Coverage Flags</span>
              </h4>
              <ul className="space-y-1.5 pl-1">
                {credibility.uncertainty_flags.map((flag, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-amber-900">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" aria-hidden="true" />
                    <span>{flag}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
