import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { UseFormReturn } from 'react-hook-form';
import { CitizenReportFormValues, SeverityType } from '@/types';

interface SeveritySectionProps {
  form: UseFormReturn<CitizenReportFormValues>;
}

const SEVERITY_OPTIONS: { value: SeverityType; label: string }[] = [
  { value: 'LOW', label: 'Low' },
  { value: 'MODERATE', label: 'Moderate' },
  { value: 'HIGH', label: 'High' },
  { value: 'SEVERE', label: 'Severe' },
];

export const SeveritySection: React.FC<SeveritySectionProps> = ({ form }) => {
  const { setValue, watch } = form;
  const currentSeverity = watch('severity');

  const handleSelectSeverity = (val: SeverityType) => {
    setValue('severity', val, { shouldValidate: true });
  };

  const getSeverityStyle = (val: SeverityType, isSelected: boolean) => {
    if (!isSelected) {
      return 'border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50';
    }

    switch (val) {
      case 'LOW':
        return 'border-2 border-emerald-500 bg-emerald-50 text-emerald-900 shadow-sm';
      case 'MODERATE':
        return 'border-2 border-amber-400 bg-amber-50/60 text-amber-950 shadow-sm';
      case 'HIGH':
        return 'border-2 border-orange-500 bg-orange-50 text-orange-950 shadow-sm';
      case 'SEVERE':
        return 'border-2 border-rose-600 bg-rose-50 text-rose-950 shadow-sm font-bold';
      default:
        return 'border-2 border-blue-600 bg-blue-50 text-blue-900';
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">How severe is it?</h2>
      </div>

      {/* 2x2 grid or 4 columns */}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {SEVERITY_OPTIONS.map((opt) => {
          const isSelected = currentSeverity === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSelectSeverity(opt.value)}
              className={`flex h-12 items-center justify-center rounded-xl text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-blue-600/30 ${getSeverityStyle(
                opt.value,
                isSelected
              )}`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
