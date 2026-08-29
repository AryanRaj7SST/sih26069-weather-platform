import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, CheckSquare, Layers, ArrowRight, ArrowLeft, Building2, Radio } from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';

export const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />

      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-xl space-y-6">
          {/* Main Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs space-y-6">
            {/* Header */}
            <div className="flex items-start space-x-3.5">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
                <ShieldCheck className="h-6 w-6" aria-hidden="true" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 border border-blue-200/80 px-2.5 py-0.5 rounded-full">
                    Operator Access
                  </span>
                  <span className="flex items-center space-x-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full">
                    <Radio className="h-2.5 w-2.5 text-emerald-500 animate-pulse" aria-hidden="true" />
                    <span>Control Room Live</span>
                  </span>
                </div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 mt-1">
                  Emergency Operations Portal
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5">
                  DEOC / SDRF / NDRF Control Room
                </p>
              </div>
            </div>

            {/* Context & Scope Note */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-xs text-slate-600 space-y-2">
              <div className="flex items-center space-x-2 text-slate-900 font-bold">
                <Building2 className="h-4 w-4 text-slate-600" aria-hidden="true" />
                <span>Operational Triage Environment (MVP)</span>
              </div>
              <p className="leading-relaxed text-[11px] text-slate-500">
                This portal gateway provides authorized disaster management operators with direct access to live report triage queues, AI explainable credibility breakdowns, and multi-source meteorological corroboration telemetry.
              </p>
            </div>

            {/* Institutional Reviewer Identity */}
            <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 space-y-2">
              <div className="text-[10px] font-extrabold uppercase tracking-wider text-blue-700">
                Institutional Reviewer Role Context
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 block font-medium">Designated Role</span>
                  <span className="font-bold text-slate-900">DEOC Officer</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-medium">Audit Identity</span>
                  <span className="font-mono font-bold text-slate-800 text-[11px]">officer@deoc.gov.in</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3 pt-2">
              <Link
                to="/admin/queue"
                className="w-full flex items-center justify-between px-5 py-3.5 rounded-xl bg-blue-600 text-white font-bold text-sm hover:bg-blue-700 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
              >
                <div className="flex items-center space-x-2.5">
                  <CheckSquare className="h-4 w-4" aria-hidden="true" />
                  <span>Open Verification Queue</span>
                </div>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>

              <Link
                to="/incidents"
                className="w-full flex items-center justify-between px-5 py-3.5 rounded-xl border border-slate-200 bg-white text-slate-800 font-bold text-sm hover:bg-slate-50 hover:border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
              >
                <div className="flex items-center space-x-2.5">
                  <Layers className="h-4 w-4 text-slate-500" aria-hidden="true" />
                  <span>Open Incident Intelligence</span>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
              </Link>
            </div>

            {/* Back link */}
            <div className="pt-2 border-t border-slate-100 flex justify-center">
              <Link
                to="/"
                className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Return to Public Home</span>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
