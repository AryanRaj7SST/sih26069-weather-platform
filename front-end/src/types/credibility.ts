// Machine Credibility Assessment Domain Types

export interface IncidentCredibilityData {
  incident_id: string;
  score: number; // 0.0 - 1.0
  is_machine_assessed: boolean;
  label: string;
  base_trust_prior: number;
  explanation_text: string;
  positive_drivers: string[];
  negative_drivers: string[];
  uncertainty_flags: string[];
  last_calculated_at: string;
}
