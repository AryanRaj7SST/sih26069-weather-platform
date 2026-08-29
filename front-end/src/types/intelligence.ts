// Intelligence Pipeline Orchestration Readiness and Stage Telemetry

import { OverallReadiness, StageOutcome } from './enums';

export interface StageStatusSummary {
  status: StageOutcome;
  attempt: number;
  duration_ms: number | null;
  error_message: string | null;
  summary: string | null;
}

export interface IncidentIntelligenceData {
  incident_id: string;
  overall_readiness: OverallReadiness;
  last_successful_stage: string | null;
  stages: Record<string, StageStatusSummary>;
}
