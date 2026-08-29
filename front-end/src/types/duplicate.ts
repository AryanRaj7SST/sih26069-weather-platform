// Semantic Duplicate Cluster Domain Types

export interface ClusterMemberSummary {
  report_id: string;
  tracking_id: string;
  title: string;
  similarity_score: number;
  occurred_at: string | null;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface IncidentClusterDetailData {
  cluster_id: string;
  cluster_code: string;
  total_member_count: number;
  is_representative: boolean;
  representative_report_id: string;
  temporal_span_hours: number | null;
  members: ClusterMemberSummary[];
}
