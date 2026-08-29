// Physical AWS & CWC Corroborating Observation Domain Types

import { ObservationRelationship } from './enums';

export interface ObservationMetricSummary {
  rainfall_mm: number | null;
  water_level_m: number | null;
  wind_speed_kmh: number | null;
}

export interface IncidentObservationItemData {
  corroboration_id: string;
  observation_id: string;
  station_code: string | null;
  station_name: string | null;
  source_code: string;
  observed_at: string | null;
  distance_km: number | null;
  relationship: ObservationRelationship;
  corroboration_score: number;
  is_contradiction: boolean;
  metrics: ObservationMetricSummary;
  is_human_override: boolean;
}
