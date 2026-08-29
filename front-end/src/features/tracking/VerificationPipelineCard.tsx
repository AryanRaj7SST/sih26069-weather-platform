import React from 'react';
import { CheckCircle2, Clock, ShieldCheck, AlertCircle } from 'lucide-react';
import { ReportDetailData } from '@/types';

interface VerificationPipelineCardProps {
  report: ReportDetailData;
}

export const VerificationPipelineCard: React.FC<VerificationPipelineCardProps> = ({
  report,
}) => {
  const isProcessingCompleted = report.processing_status === 'COMPLETED';
  const isProcessingQueued = report.processing_status === 'QUEUED' || !report.processing_status;
  const isVerified = report.verification_status === 'VERIFIED';
  const isUnderReview = report.verification_status === 'UNDER_REVIEW';
  const isRejected = report.verification_status === 'REJECTED';

  const formatStepTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + ' UTC';
    } catch {
      return '';
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Verification Pipeline</h3>
        </div>
        <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
          Stage: {report.processing_status || 'QUEUED'}
        </span>
      </div>

      <div className="mt-6 space-y-6">
        {/* Stage 1: Received & Ingested (REAL COMPLETED STATE) */}
        <div className="relative flex items-start space-x-3.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-slate-900">Report Ingested & Validated</p>
              <span className="font-mono text-xs text-slate-400">
                {formatStepTime(report.created_at)}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              Citizen observation successfully persisted. Geospatial coordinates, observation time, and metadata schema validated.
            </p>
          </div>
        </div>

        {/* Stage 2: Automated Processing Pipeline (REAL STATE: QUEUED / NOT STARTED) */}
        <div className="relative flex items-start space-x-3.5">
          <div
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
              isProcessingCompleted
                ? 'bg-emerald-100 text-emerald-600'
                : 'bg-blue-100 text-blue-700'
            }`}
          >
            {isProcessingCompleted ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <Clock className="h-4 w-4 text-blue-600" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-slate-900">Automated Pipeline Processing</p>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  isProcessingCompleted
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-blue-50 text-blue-700'
                }`}
              >
                {report.processing_status || 'QUEUED'}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              {isProcessingCompleted
                ? 'Automated hazard classification, spatial duplicate clustering, and telemetry corroboration finished.'
                : isProcessingQueued
                ? 'Report is queued. Automated NLP classification, geospatial clustering, and AWS sensor corroboration will execute in a future pipeline phase.'
                : `Pipeline execution status: ${report.processing_status}.`}
            </p>
          </div>
        </div>

        {/* Stage 3: Authority Verification (REAL STATE: PENDING) */}
        <div className="relative flex items-start space-x-3.5">
          <div
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
              isVerified
                ? 'bg-emerald-100 text-emerald-600'
                : isRejected
                ? 'bg-rose-100 text-rose-600'
                : isUnderReview
                ? 'bg-amber-100 text-amber-600'
                : 'bg-slate-100 text-slate-400'
            }`}
          >
            {isVerified ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : isRejected ? (
              <AlertCircle className="h-4 w-4" />
            ) : (
              <Clock className="h-4 w-4" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-slate-900">Authority Verification</p>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  isVerified
                    ? 'bg-emerald-50 text-emerald-700'
                    : isRejected
                    ? 'bg-rose-50 text-rose-700'
                    : isUnderReview
                    ? 'bg-amber-50 text-amber-700'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {report.verification_status || 'PENDING'}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              {isVerified
                ? 'Official verification completed by disaster management authorities.'
                : isRejected
                ? 'Report evaluated and dismissed by authority operator.'
                : isUnderReview
                ? 'Currently under review by disaster management operator.'
                : 'Awaiting review and emergency response clearance by authorized operators (NDRF / SDRF / DEOC).'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
