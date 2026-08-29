// Digital Evidence Domain Types

import { EvidenceRelationship } from './enums';

export interface IncidentEvidenceItemData {
  link_id: string;
  evidence_id: string;
  evidence_type: string;
  publisher_domain: string;
  title: string | null;
  text_snippet: string | null;
  published_at: string;
  relationship: EvidenceRelationship;
  confidence_score: number;
  url: string | null;
  is_human_override: boolean;
}
