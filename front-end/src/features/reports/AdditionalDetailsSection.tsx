import React from 'react';
import { FileText } from 'lucide-react';
import { UseFormReturn } from 'react-hook-form';
import { CitizenReportFormValues } from '@/types';

interface AdditionalDetailsSectionProps {
  form: UseFormReturn<CitizenReportFormValues>;
}

export const AdditionalDetailsSection: React.FC<AdditionalDetailsSectionProps> = ({
  form,
}) => {
  const { register, formState: { errors } } = form;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <FileText className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Additional Details</h2>
      </div>

      <div className="mt-5 space-y-4">
        {/* Report Title */}
        <div>
          <label
            htmlFor="title"
            className="block text-sm font-semibold text-slate-700"
          >
            Report Title <span className="text-xs font-normal text-slate-500">(Brief summary)</span>
          </label>
          <input
            id="title"
            type="text"
            {...register('title')}
            placeholder="e.g., Flash flooding on Main St."
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          />
          {errors.title && (
            <p className="mt-1.5 text-xs font-medium text-rose-600">
              {errors.title.message || 'Report title is required.'}
            </p>
          )}
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="description"
            className="block text-sm font-semibold text-slate-700"
          >
            Description <span className="text-xs font-normal text-slate-500">(Optional)</span>
          </label>
          <textarea
            id="description"
            rows={4}
            {...register('description')}
            placeholder="Provide any additional observations (e.g., water depth, structural damage, direction of storm)."
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          />
          {errors.description && (
            <p className="mt-1.5 text-xs font-medium text-rose-600">
              {errors.description.message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
