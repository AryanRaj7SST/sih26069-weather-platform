// Semantic Duplicate Cluster Topology Section

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Copy, ExternalLink, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import { incidentApi } from '@/services/incidentApi';
import { incidentKeys } from '@/lib/queryKeys';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { VerificationStatus } from '@/types';

interface DuplicateClusterSectionProps {
  incidentId: string;
  clusterSize?: number;
  verificationStatus?: VerificationStatus;
}

export const DuplicateClusterSection: React.FC<DuplicateClusterSectionProps> = ({
  incidentId,
  verificationStatus,
}) => {
  const { data: response, isLoading, isError, error, refetch } = useQuery({
    queryKey: incidentKeys.cluster(incidentId),
    queryFn: ({ signal }) => incidentApi.getIncidentCluster(incidentId, signal),
    staleTime: 1000 * 60, // 1 minute
  });

  const cluster = response?.data;
  const isMarkedDuplicate = verificationStatus === 'DUPLICATE';

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <Copy className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900">
              Duplicate Incident Cluster
            </h3>
            <span className="text-[11px] text-slate-400 font-medium block">
              Automated spatial-temporal & semantic duplicate grouping
            </span>
          </div>
        </div>

        {cluster && (
          <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-2.5 py-1 rounded-lg">
            {cluster.total_member_count === 1
              ? '1 Report'
              : `${cluster.total_member_count} Grouped Reports`}
          </span>
        )}
      </div>

      {isLoading ? (
        <LoadingSkeleton count={2} className="h-20" />
      ) : isError ? (
        <ErrorCard
          title="Cluster Topology Unavailable"
          message={error instanceof Error ? error.message : 'Unable to retrieve duplicate cluster topology.'}
          onRetry={() => refetch()}
        />
      ) : !cluster || cluster.total_member_count <= 1 ? (
        isMarkedDuplicate ? (
          <EmptyState
            title="Marked as Duplicate"
            description="This incident is classified as a duplicate report. The current automated cluster contains 1 report."
            icon={Copy}
          />
        ) : (
          <EmptyState
            title="Single Incident Record"
            description="No duplicate citizen reports have been detected within the spatial-temporal matching window for this incident."
            icon={Info}
          />
        )
      ) : (
        <div className="space-y-3 pt-3 border-t border-slate-100 text-xs">
          {/* Informational Banner */}
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-3 text-indigo-950 flex items-start space-x-2.5">
            <Info className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" aria-hidden="true" />
            <p className="text-[11px] leading-relaxed">
              These <span className="font-bold">{cluster.total_member_count} reports</span> are clustered as describing the same ground-truth event across a {cluster.temporal_span_hours != null ? `${cluster.temporal_span_hours}h` : 'temporal'} window.
            </p>
          </div>

          {/* Cluster Members Table */}
          <div className="rounded-xl border border-slate-200/80 overflow-hidden">
            <div className="bg-slate-50 px-3.5 py-2 border-b border-slate-200/80 text-[10px] font-extrabold uppercase tracking-wider text-slate-500 grid grid-cols-12 gap-2">
              <span className="col-span-4">Tracking ID</span>
              <span className="col-span-5">Report Title</span>
              <span className="col-span-3 text-right">Similarity</span>
            </div>

            <div className="divide-y divide-slate-100 bg-white">
              {cluster.members.map((member) => {
                const isCurrent = member.report_id === incidentId || member.tracking_id === incidentId;
                const isRep = member.report_id === cluster.representative_report_id;

                return (
                  <div
                    key={member.report_id}
                    className={`px-3.5 py-2.5 grid grid-cols-12 gap-2 items-center text-xs ${
                      isCurrent ? 'bg-indigo-50/40' : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="col-span-4 flex items-center space-x-1.5 font-mono">
                      <span className="font-bold text-slate-800 truncate">{member.tracking_id}</span>
                      {isRep && (
                        <span className="bg-emerald-100 text-emerald-800 text-[9px] font-extrabold px-1.5 py-0.2 rounded shrink-0">
                          ANCHOR
                        </span>
                      )}
                    </div>

                    <div className="col-span-5 truncate">
                      <span className="text-slate-700 font-medium truncate block">{member.title}</span>
                      <span className="text-[10px] text-slate-400 block">{member.location_name || 'Coordinates'}</span>
                    </div>

                    <div className="col-span-3 text-right flex items-center justify-end space-x-2">
                      <span className="font-mono font-bold text-slate-900 text-[11px]">
                        {(member.similarity_score * 100).toFixed(0)}%
                      </span>
                      {!isCurrent && (
                        <Link
                          to={`/incidents/${encodeURIComponent(member.report_id || member.tracking_id)}`}
                          className="text-blue-600 hover:text-blue-800"
                          title="View this member report"
                        >
                          <ExternalLink className="h-3 w-3" aria-hidden="true" />
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
