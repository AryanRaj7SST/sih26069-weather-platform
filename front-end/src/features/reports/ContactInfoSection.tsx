import React from 'react';
import { User } from 'lucide-react';
import { UseFormReturn } from 'react-hook-form';
import { CitizenReportFormValues } from '@/types';

interface ContactInfoSectionProps {
  form: UseFormReturn<CitizenReportFormValues>;
}

export const ContactInfoSection: React.FC<ContactInfoSectionProps> = ({ form }) => {
  const { register } = form;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <User className="h-5 w-5" />
        </div>
        <div className="flex items-baseline space-x-2">
          <h2 className="text-lg font-bold text-slate-900">Contact Info</h2>
          <span className="text-xs font-normal text-slate-500">(Optional)</span>
        </div>
      </div>

      <p className="mt-2 text-xs leading-relaxed text-slate-500">
        Provide your details if you consent to being contacted by meteorologists for follow-up verification.
      </p>

      <div className="mt-4 space-y-3">
        <div>
          <input
            id="contact_name"
            type="text"
            {...register('contact_name')}
            placeholder="Full Name"
            className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          />
        </div>

        <div>
          <input
            id="contact_info"
            type="text"
            {...register('contact_info')}
            placeholder="Email address or Phone number"
            className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          />
        </div>
      </div>
    </div>
  );
};
