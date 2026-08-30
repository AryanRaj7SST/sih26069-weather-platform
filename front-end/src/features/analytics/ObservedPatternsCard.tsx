import React, { useMemo } from 'react';
import { Info, CheckCircle2, TrendingUp } from 'lucide-react';
import { DashboardSummaryData, ReportDetailData } from '@/types';

interface ObservedPatternsCardProps {
  summary?: DashboardSummaryData;
  reports?: ReportDetailData[];
  isLoading: boolean;
}

export const ObservedPatternsCard: React.FC<ObservedPatternsCardProps> = ({
  summary,
  reports = [],
  isLoading,
}) => {
  const observations = useMemo(() => {
    // 1. Authoritative summary data derivation
    if (summary) {
      if (summary.total_count === 0) return [];

      const items: string[] = [];

      // 1. Top Hazard Observation
      const topCategory = summary.category_distribution[0];
      if (topCategory && topCategory.count > 0) {
        items.push(
          `${topCategory.category_name} reports constitute the highest activity volume (${topCategory.count} reports, ${topCategory.percentage}% of total) in the selected period.`
        );
      }

      // 2. Severe / Critical Urgency Observation
      const severeHighCount = summary.severity.severe_high_count;
      if (severeHighCount > 0) {
        const severePct = Math.round((severeHighCount / summary.total_count) * 100);
        items.push(
          `${severeHighCount} reports (${severePct}%) are classified as High or Severe urgency requiring prioritized operator monitoring.`
        );
      }

      // 3. Verification Ratio Observation
      const verifiedCount = summary.verification.verified_count;
      const verifiedPct = summary.verification.verified_rate;
      items.push(
        `Verified report rate is currently at ${verifiedPct}% (${verifiedCount} verified reports) across active submissions.`
      );

      return items;
    }

    // 2. Legacy fallback
    if (reports.length === 0) return [];

    const items: string[] = [];

    // 1. Top Hazard Observation
    const catCounts: Record<string, number> = {};
    for (const r of reports) {
      const title = r.category?.title || r.title || 'Hazard';
      catCounts[title] = (catCounts[title] || 0) + 1;
    }
    const topCategory = Object.entries(catCounts).sort((a, b) => b[1] - a[1])[0];
    if (topCategory) {
      const pct = Math.round((topCategory[1] / reports.length) * 100);
      items.push(
        `${topCategory[0]} reports constitute the highest activity volume (${topCategory[1]} reports, ${pct}% of total) in the selected period.`
      );
    }

    // 2. Severe / Critical Urgency Observation
    const severeCount = reports.filter(
      (r) => r.severity === 'SEVERE' || r.severity === 'HIGH'
    ).length;
    if (severeCount > 0) {
      const severePct = Math.round((severeCount / reports.length) * 100);
      items.push(
        `${severeCount} reports (${severePct}%) are classified as High or Severe urgency requiring prioritized operator monitoring.`
      );
    }

    // 3. Verification Ratio Observation
    const verifiedCount = reports.filter((r) => r.verification_status === 'VERIFIED').length;
    const verifiedPct = Math.round((verifiedCount / reports.length) * 100);
    items.push(
      `Verified report rate is currently at ${verifiedPct}% (${verifiedCount} verified reports) across active submissions.`
    );

    return items;
  }, [summary, reports]);

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-4 shadow-sm animate-pulse">
        <div className="h-4 w-48 bg-blue-200 rounded" />
      </div>
    );
  }

  if (observations.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex items-center space-x-3 text-xs text-slate-500">
        <Info className="h-4 w-4 text-slate-400 flex-shrink-0" />
        <span>No significant pattern observations found for the selected dataset.</span>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4 sm:p-5 shadow-sm">
      <div className="flex items-start space-x-3">
        <div className="rounded-xl bg-blue-600/10 p-2 text-blue-600 flex-shrink-0">
          <TrendingUp className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-900">
              Observed Patterns
            </h3>
            <span className="text-[10px] text-blue-700/80 font-medium">
              Deterministic rule-based summary
            </span>
          </div>

          <ul className="mt-2 space-y-1.5 text-xs text-blue-950 font-medium leading-relaxed">
            {observations.map((obs, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-blue-600 flex-shrink-0 mt-0.5" />
                <span>{obs}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
