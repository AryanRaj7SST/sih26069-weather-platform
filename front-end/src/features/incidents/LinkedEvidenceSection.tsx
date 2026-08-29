// Linked Digital Evidence Section

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, ExternalLink, Globe, ChevronLeft, ChevronRight } from 'lucide-react';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { formatDateTime, formatEvidenceRelationship } from '@/lib/presentation';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';

interface LinkedEvidenceSectionProps {
  incidentId: string;
  totalCount?: number;
}

export const LinkedEvidenceSection: React.FC<LinkedEvidenceSectionProps> = ({
  incidentId,
  totalCount,
}) => {
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const { data: response, isLoading, isError, error, refetch } = useQuery({
    queryKey: incidentKeys.evidence(incidentId, page),
    queryFn: ({ signal }) => incidentApi.getIncidentEvidence(incidentId, page, pageSize, signal),
    staleTime: 1000 * 60, // 1 minute
  });

  const evidenceItems = response?.data || [];
  const pagination = response?.pagination;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              Corroborating Digital Evidence
            </h3>
            <span className="text-[11px] text-slate-400 font-medium block">
              Multi-source open web and social broadcast verification feeds
            </span>
          </div>
        </div>

        {totalCount !== undefined && (
          <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
            {totalCount} {totalCount === 1 ? 'Item' : 'Items'}
          </span>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton count={2} className="h-24" />
      ) : isError ? (
        <ErrorCard
          title="Digital Evidence Unavailable"
          message={error instanceof Error ? error.message : 'Unable to retrieve linked evidence records.'}
          onRetry={() => refetch()}
        />
      ) : evidenceItems.length === 0 ? (
        <EmptyState
          title="No Digital Evidence Linked"
          description="No open-web news articles or public feeds have matched this incident yet."
        />
      ) : (
        <div className="space-y-3 pt-3 border-t border-slate-100">
          <div className="space-y-3">
            {evidenceItems.map((item) => {
              const relStyle = formatEvidenceRelationship(item.relationship);
              const confScore = Math.round(item.confidence_score * 100);

              return (
                <div
                  key={item.link_id || item.evidence_id}
                  className="rounded-xl border border-slate-200/80 bg-slate-50/40 p-3.5 space-y-2 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center space-x-1 text-[11px] font-bold text-slate-700 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                        <Globe className="h-3 w-3 text-slate-400" aria-hidden="true" />
                        <span>{item.publisher_domain || 'Open Web'}</span>
                      </span>
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold border ${relStyle.badgeClass}`}
                      >
                        {relStyle.label}
                      </span>
                    </div>

                    <div className="text-[10px] text-slate-400 font-mono">
                      <span>Match Confidence: </span>
                      <span className="font-bold text-slate-700">{confScore}%</span>
                    </div>
                  </div>

                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 leading-snug">
                    {item.title || 'Broadcast Record'}
                  </h4>

                  {item.text_snippet && (
                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                      {item.text_snippet}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1.5 border-t border-slate-200/50">
                    <time dateTime={item.published_at}>{formatDateTime(item.published_at)}</time>
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 font-bold text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        <span>View Source</span>
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    )}
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
