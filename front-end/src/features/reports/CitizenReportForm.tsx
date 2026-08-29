import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Send, Loader2, AlertCircle } from 'lucide-react';
import { CitizenReportFormValues, ReportSubmitData } from '@/types';
import { submitCitizenReport } from '@/services/reportApi';
import { LocationSection } from './LocationSection';
import { CategorySection } from './CategorySection';
import { SeveritySection } from './SeveritySection';
import { AdditionalDetailsSection } from './AdditionalDetailsSection';
import { MediaUploadSection } from './MediaUploadSection';
import { ContactInfoSection } from './ContactInfoSection';
import { ReportSuccessModal } from './ReportSuccessModal';

const reportFormSchema = z.object({
  latitude: z
    .number({ required_error: 'Please provide location coordinates using GPS or landmark' })
    .min(-90, 'Invalid latitude')
    .max(90, 'Invalid latitude'),
  longitude: z
    .number({ required_error: 'Please provide location coordinates using GPS or landmark' })
    .min(-180, 'Invalid longitude')
    .max(180, 'Invalid longitude'),
  location_name: z.string().optional(),
  category_code: z.string().min(1, 'Please select what weather event you are observing'),
  severity: z.enum(['LOW', 'MODERATE', 'HIGH', 'SEVERE']),
  title: z
    .string()
    .min(3, 'Title must be at least 3 characters long')
    .max(255, 'Title cannot exceed 255 characters'),
  description: z.string().max(5000, 'Description cannot exceed 5000 characters').optional(),
  occurred_at: z.string().optional(),
  contact_name: z.string().optional(),
  contact_info: z.string().optional(),
});

export const CitizenReportForm: React.FC = () => {
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<ReportSubmitData | null>(null);

  const form = useForm<CitizenReportFormValues>({
    resolver: zodResolver(reportFormSchema),
    defaultValues: {
      latitude: 19.0760, // Default fallback (Mumbai central) if GPS not used
      longitude: 72.8777,
      location_name: '',
      category_code: 'HEAVY_RAINFALL',
      severity: 'MODERATE',
      title: '',
      description: '',
      contact_name: '',
      contact_info: '',
    },
  });

  const onSubmit = async (values: CitizenReportFormValues) => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await submitCitizenReport(values, mediaFiles);
      setSuccessData(response.data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSubmitError(err.message);
      } else {
        setSubmitError('An unexpected error occurred while submitting your report. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    form.reset();
    setMediaFiles([]);
    setSuccessData(null);
    setSubmitError(null);
  };

  return (
    <>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Error Banner */}
        {submitError && (
          <div className="flex items-start space-x-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 shadow-sm">
            <AlertCircle className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold">Submission Failed</p>
              <p className="mt-0.5 text-xs text-rose-700">{submitError}</p>
            </div>
          </div>
        )}

        {/* 1. Where did this happen? */}
        <LocationSection form={form} />

        {/* 2. What are you observing? */}
        <CategorySection form={form} />

        {/* 3. How severe is it? */}
        <SeveritySection form={form} />

        {/* 4. Additional Details */}
        <AdditionalDetailsSection form={form} />

        {/* 5. Upload Photo or Video */}
        <MediaUploadSection
          mediaFiles={mediaFiles}
          setMediaFiles={setMediaFiles}
        />

        {/* 6. Contact Info (Optional) */}
        <ContactInfoSection form={form} />

        {/* 7. Submit Action */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center space-x-2 rounded-xl bg-blue-600 px-6 py-4 text-base font-bold text-white shadow-lg shadow-blue-600/20 transition-all hover:bg-blue-700 hover:shadow-blue-600/30 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Submitting Weather Report...</span>
              </>
            ) : (
              <>
                <Send className="h-5 w-5" />
                <span>Submit Weather Report</span>
              </>
            )}
          </button>

          <p className="mt-3 text-center text-xs leading-normal text-slate-500">
            By submitting, you agree to our Terms of Service regarding user-generated content.
          </p>
        </div>
      </form>

      {/* Success Modal */}
      {successData && (
        <ReportSuccessModal data={successData} onReset={handleReset} />
      )}
    </>
  );
};
