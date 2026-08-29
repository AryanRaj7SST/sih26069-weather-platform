import React, { useState } from 'react';
import { CheckCircle2, Copy, Check, ArrowRight } from 'lucide-react';
import { ReportSubmitData } from '@/types';

interface ReportSuccessModalProps {
  data: ReportSubmitData;
  onReset: () => void;
}

export const ReportSuccessModal: React.FC<ReportSuccessModalProps> = ({
  data,
  onReset,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(data.tracking_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 md:p-8 shadow-xl border border-slate-100">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle2 className="h-10 w-10" />
          </div>

          <h3 className="mt-4 text-2xl font-bold text-slate-900">
            Report Submitted Successfully!
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            Thank you for contributing real-time weather observations. Your report is now queued for validation.
          </p>

          {/* Tracking ID Card */}
          <div className="mt-6 w-full rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
              Your Public Tracking Identifier
            </p>
            <div className="mt-1 flex items-center justify-between">
              <span className="font-mono text-xl font-bold tracking-tight text-blue-950">
                {data.tracking_id}
              </span>
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center space-x-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 shadow-sm border border-blue-200 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy ID</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Status Breakdown */}
          <div className="mt-4 grid w-full grid-cols-2 gap-3 text-left">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="text-[11px] font-medium text-slate-500 uppercase">Processing State</span>
              <p className="mt-0.5 text-sm font-semibold text-blue-700">
                {data.processing_status}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="text-[11px] font-medium text-slate-500 uppercase">Verification</span>
              <p className="mt-0.5 text-sm font-semibold text-amber-700">
                {data.verification_status}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="mt-8 flex w-full flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={onReset}
              className="flex-1 rounded-xl border border-slate-300 bg-white py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              Submit Another Report
            </button>
            <a
              href={`/track-report?id=${encodeURIComponent(data.tracking_id)}`}
              className="flex flex-1 items-center justify-center space-x-2 rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
            >
              <span>Track This Report</span>
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
