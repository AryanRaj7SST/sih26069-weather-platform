import React from 'react';
import { Upload, FileCheck, ShieldCheck } from 'lucide-react';

export const ProcessFlowCard: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <h2 className="text-lg font-bold text-slate-900 pb-4 border-b border-slate-100">
        How reports are processed
      </h2>

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-6 relative">
        {/* Step 1 */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-md">
            <Upload className="h-5 w-5" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-slate-900">Report Submitted</h3>
          <p className="mt-1 text-xs text-slate-500">Citizen report logged</p>
        </div>

        {/* Step 2 */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 border border-slate-300 text-slate-700 shadow-sm">
            <FileCheck className="h-5 w-5 text-blue-600" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-slate-900">Automated Processing</h3>
          <p className="mt-1 text-xs text-slate-500">Data scrubbed and flagged</p>
        </div>

        {/* Step 3 */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-600 text-white shadow-md">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-slate-900">Authority Review</h3>
          <p className="mt-1 text-xs text-slate-500">Reviewed by officials</p>
        </div>
      </div>
    </div>
  );
};
