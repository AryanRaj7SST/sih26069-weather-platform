// Canonical Domain & Operational Enums mirroring backend models

export type SeverityType = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';

export type VerificationStatus =
  | 'PENDING'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'DUPLICATE';

export type OverallReadiness =
  | 'INTELLIGENCE_READY'
  | 'INTELLIGENCE_PARTIAL'
  | 'INTELLIGENCE_PENDING'
  | 'INTELLIGENCE_FAILED';

export type StageName =
  | 'LOCATION'
  | 'DUPLICATE'
  | 'EVIDENCE'
  | 'OBSERVATION'
  | 'CREDIBILITY';

export type StageOutcome =
  | 'SUCCESS_WITH_RESULTS'
  | 'SUCCESS_WITH_NO_MATCH'
  | 'SUCCESS_WITH_INSUFFICIENT_DATA'
  | 'SKIPPED_NOT_APPLICABLE'
  | 'SKIPPED_STALE'
  | 'RETRYABLE_FAILURE'
  | 'PERMANENT_FAILURE';

export type EvidenceRelationship =
  | 'SUPPORTING'
  | 'RELATED'
  | 'CONTEXTUAL'
  | 'CONTRADICTORY'
  | 'IRRELEVANT';

export type ObservationRelationship =
  | 'CORROBORATING'
  | 'CONSISTENT'
  | 'WEAK'
  | 'CONTRADICTORY'
  | 'IRRELEVANT'
  | 'INSUFFICIENT_DATA';

export type HazardCategoryCode =
  | 'FLOOD_WATERLOGGING'
  | 'HEAVY_RAINFALL'
  | 'CYCLONE_STORM'
  | 'URBAN_FLOOD'
  | 'EXTREME_HEAT'
  | 'HAILSTORM'
  | 'LANDSLIDE'
  | 'THUNDERSTORM_LIGHTNING'
  | 'DROUGHT'
  | 'OTHER';

export type RejectionReasonCode =
  | 'INACCURATE_LOCATION'
  | 'HOAX_SPAM'
  | 'NORMAL_WEATHER'
  | 'OUTDATED_EVENT'
  | 'OTHER';
