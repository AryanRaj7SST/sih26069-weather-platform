export type SeverityType = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';

export interface WeatherCategoryOption {
  code: string;
  title: string;
  iconName: string;
  description?: string;
}

export interface CitizenReportFormValues {
  latitude: number;
  longitude: number;
  location_name?: string;
  category_code: string;
  severity: SeverityType;
  title: string;
  description?: string;
  occurred_at?: string;
  contact_name?: string;
  contact_info?: string;
}

export interface ReportSubmitData {
  id: string;
  tracking_id: string;
  processing_status: string;
  verification_status: string;
  submitted_at: string;
  media_count: number;
}

export interface ReportSubmitResponse {
  success: boolean;
  data: ReportSubmitData;
  meta: {
    timestamp: string;
    request_id?: string;
  };
}
