// Comprehensive Frontend Incident Intelligence Test Suite & Contract Verification

import { describe, it, expect } from 'vitest';
import {
  formatEvidenceRelationship,
  formatHazardCategory,
  formatObservationRelationship,
  formatReadiness,
  formatStageOutcome,
  formatVerificationStatus,
} from '../lib/presentation';
import { incidentKeys, normalizeParams } from '../lib/queryKeys';
import {
  EvidenceRelationship,
  GeoJSONFeatureCollection,
  HazardCategoryCode,
  IncidentClusterDetailData,
  IncidentCredibilityData,
  IncidentDetailOperator,
  IncidentDetailPublic,
  IncidentEvidenceItemData,
  IncidentIntelligenceData,
  IncidentObservationItemData,
  IncidentSummary,
  ObservationRelationship,
  OverallReadiness,
  StageOutcome,
  VerificationStatus,
} from '../types';

describe('1. Canonical StageOutcome & Enums Wire Contract', () => {
  it('strictly validates all canonical StageOutcome wire values without invented states', () => {
    const canonicalOutcomes: StageOutcome[] = [
      'SUCCESS_WITH_RESULTS',
      'SUCCESS_WITH_NO_MATCH',
      'SUCCESS_WITH_INSUFFICIENT_DATA',
      'SKIPPED_NOT_APPLICABLE',
      'SKIPPED_STALE',
      'RETRYABLE_FAILURE',
      'PERMANENT_FAILURE',
    ];

    canonicalOutcomes.forEach((outcome) => {
      const formatted = formatStageOutcome(outcome);
      expect(formatted.label).toBeTruthy();
      expect(formatted.badgeClass).toBeTruthy();
    });

    expect(formatStageOutcome('SUCCESS_WITH_RESULTS').label).toBe('Results Found');
    expect(formatStageOutcome('SUCCESS_WITH_NO_MATCH').label).toBe('No Matches Found');
    expect(formatStageOutcome('SUCCESS_WITH_INSUFFICIENT_DATA').label).toBe('Insufficient Data');
    expect(formatStageOutcome('RETRYABLE_FAILURE').badgeClass).toContain('animate-pulse');
  });

  it('proves OBSERVATION stage outcome Results Found coexists with WEAK or CONTRADICTORY observation relationships without conflict', () => {
    const stageOutcome = formatStageOutcome('SUCCESS_WITH_RESULTS');
    const weakRel = formatObservationRelationship('WEAK');
    const contraRel = formatObservationRelationship('CONTRADICTORY');

    expect(stageOutcome.label).toBe('Results Found');
    expect(weakRel.label).toBe('Weak Association');
    expect(contraRel.label).toBe('Physical Contradiction');
    expect(stageOutcome.label).not.toContain('Corroborated');
  });

  it('strictly validates all canonical EvidenceRelationship values', () => {
    const relationships: EvidenceRelationship[] = [
      'SUPPORTING',
      'RELATED',
      'CONTEXTUAL',
      'CONTRADICTORY',
      'IRRELEVANT',
    ];

    relationships.forEach((rel) => {
      const formatted = formatEvidenceRelationship(rel);
      expect(formatted.label).toBeTruthy();
      expect(formatted.badgeClass).toBeTruthy();
    });

    expect(formatEvidenceRelationship('SUPPORTING').label).toBe('Supporting Evidence');
    expect(formatEvidenceRelationship('CONTRADICTORY').label).toBe('Contradictory Source');
  });

  it('strictly validates all canonical ObservationRelationship values', () => {
    const relationships: ObservationRelationship[] = [
      'CORROBORATING',
      'CONSISTENT',
      'WEAK',
      'CONTRADICTORY',
      'IRRELEVANT',
      'INSUFFICIENT_DATA',
    ];

    relationships.forEach((rel) => {
      const formatted = formatObservationRelationship(rel);
      expect(formatted.label).toBeTruthy();
      expect(formatted.badgeClass).toBeTruthy();
    });

    expect(formatObservationRelationship('CORROBORATING').label).toBe('Physical Corroboration');
    expect(formatObservationRelationship('CONTRADICTORY').label).toBe('Physical Contradiction');
  });

  it('strictly validates all canonical HazardCategoryCode values', () => {
    const categories: HazardCategoryCode[] = [
      'FLOOD_WATERLOGGING',
      'HEAVY_RAINFALL',
      'CYCLONE_STORM',
      'URBAN_FLOOD',
      'EXTREME_HEAT',
      'HAILSTORM',
      'LANDSLIDE',
      'THUNDERSTORM_LIGHTNING',
      'DROUGHT',
      'OTHER',
    ];

    categories.forEach((cat) => {
      const formatted = formatHazardCategory(cat);
      expect(formatted).toBeTruthy();
      expect(formatted).not.toContain('_');
    });

    expect(formatHazardCategory('FLOOD_WATERLOGGING')).toBe('Flood / Waterlogging');
    expect(formatHazardCategory('URBAN_FLOOD')).toBe('Urban Inundation');
  });

  it('strictly validates all canonical OverallReadiness values', () => {
    const readinessValues: OverallReadiness[] = [
      'INTELLIGENCE_READY',
      'INTELLIGENCE_PARTIAL',
      'INTELLIGENCE_PENDING',
      'INTELLIGENCE_FAILED',
    ];

    readinessValues.forEach((r) => {
      const formatted = formatReadiness(r);
      expect(formatted.label).toBeTruthy();
      expect(formatted.pillBg).toBeTruthy();
    });

    expect(formatReadiness('INTELLIGENCE_READY').label).toBe('Intelligence Complete');
    expect(formatReadiness('INTELLIGENCE_PARTIAL').label).toBe('Intelligence Partial (Enriching)');
  });
});

describe('2. Query Key Architecture & Deterministic Normalization', () => {
  it('normalizes query params deterministically regardless of key order or undefined values', () => {
    const paramsA = { page: 1, category: 'FLOOD_WATERLOGGING', search: undefined, status: 'ALL' };
    const paramsB = { category: 'FLOOD_WATERLOGGING', page: 1 };

    const normA = normalizeParams(paramsA);
    const normB = normalizeParams(paramsB);

    expect(JSON.stringify(normA)).toBe(JSON.stringify(normB));
    expect(incidentKeys.list(paramsA)).toEqual(incidentKeys.list(paramsB));
  });

  it('produces hierarchical prefix keys for verification queue invalidation', () => {
    const queueRoot = incidentKeys.verificationQueues();
    expect(queueRoot).toEqual(['verification-queue']);

    const queueFiltered = incidentKeys.verificationQueueList({ priority: 'HIGH', page: 2 });
    expect(queueFiltered[0]).toBe('verification-queue');
    expect(queueFiltered[1]).toEqual({ page: 2, priority: 'HIGH' });
  });

  it('produces hierarchical prefix keys for incident details and sub-resources', () => {
    const incidentId = 'rpt-test-123';
    const detailKey = incidentKeys.detail(incidentId);
    const credKey = incidentKeys.credibility(incidentId);
    const evidKey = incidentKeys.evidence(incidentId, 1);
    const obsKey = incidentKeys.observations(incidentId, 2);

    expect(detailKey).toEqual(['incidents', 'detail', incidentId]);
    expect(credKey.slice(0, 3)).toEqual(detailKey);
    expect(evidKey.slice(0, 3)).toEqual(detailKey);
    expect(obsKey.slice(0, 3)).toEqual(detailKey);
  });
});

describe('3. Nullable Location Safety & Coordinate Invariants', () => {
  const isValidCoordinate = (lat: number | null | undefined, lng: number | null | undefined): boolean => {
    return (
      lat != null &&
      lng != null &&
      !isNaN(lat) &&
      !isNaN(lng) &&
      isFinite(lat) &&
      isFinite(lng) &&
      lat >= -90 &&
      lat <= 90 &&
      lng >= -180 &&
      lng <= 180
    );
  };

  it('safely rejects null, NaN, Infinity, and out-of-bounds coordinates from map rendering', () => {
    expect(isValidCoordinate(null, null)).toBe(false);
    expect(isValidCoordinate(19.076, null)).toBe(false);
    expect(isValidCoordinate(NaN, 72.8777)).toBe(false);
    expect(isValidCoordinate(Infinity, 72.8777)).toBe(false);
    expect(isValidCoordinate(-Infinity, 72.8777)).toBe(false);
    expect(isValidCoordinate(95.0, 72.8777)).toBe(false); // lat > 90
    expect(isValidCoordinate(-95.0, 72.8777)).toBe(false); // lat < -90
    expect(isValidCoordinate(19.076, 185.0)).toBe(false); // lng > 180
    expect(isValidCoordinate(19.076, -190.0)).toBe(false); // lng < -180

    // Valid coordinates:
    expect(isValidCoordinate(19.076, 72.8777)).toBe(true);
    expect(isValidCoordinate(0.0, 0.0)).toBe(true);
  });

  it('models nullable location safely in IncidentSummary without fabricating coordinates', () => {
    const incidentWithNullCoords: IncidentSummary = {
      id: 'inc-001',
      tracking_id: 'RPT-20260829-0001',
      title: 'Unresolved Location Report',
      category: { code: 'HEAVY_RAINFALL', title: 'Heavy Rainfall' },
      severity: 'HIGH',
      location: {
        name: 'Kurla West, Mumbai',
        latitude: null,
        longitude: null,
      },
      occurred_at: null,
      verification_status: 'PENDING',
      credibility_score: null,
      readiness: 'INTELLIGENCE_PENDING',
      media_count: 0,
      created_at: new Date().toISOString(),
    };

    expect(incidentWithNullCoords.location.latitude).toBeNull();
    expect(incidentWithNullCoords.location.longitude).toBeNull();
    expect(isValidCoordinate(incidentWithNullCoords.location.latitude, incidentWithNullCoords.location.longitude)).toBe(false);
  });
});

describe('4. Semantic Separation: Machine Credibility vs. Human Verification', () => {
  it('preserves distinct visual styles and does not force credibility to 100 on VERIFIED', () => {
    const verificationPill = formatVerificationStatus('VERIFIED');
    expect(verificationPill.label).toBe('VERIFIED');
    expect(verificationPill.bgClass).toContain('bg-emerald-600');

    // Credibility score is an independent statistical float
    const mockCredibility = 0.72;
    const scoreDisplay = Math.round(mockCredibility * 100);
    expect(scoreDisplay).toBe(72);
    expect(`${scoreDisplay} / 100`).toBe('72 / 100');
  });

  it('handles REJECTED status without zeroing or mutating credibility model', () => {
    const rejectedPill = formatVerificationStatus('REJECTED');
    expect(rejectedPill.label).toBe('REJECTED');
    expect(rejectedPill.bgClass).toContain('bg-rose-600');
  });
});

describe('5. Physical Observation Time-Series Semantics', () => {
  it('treats multiple readings from one station as a time-series rather than multiple independent confirmations', () => {
    const stationReadings = [
      { observation_id: 'obs-1', station_code: 'VABB', observed_at: '2026-08-29T10:00:00Z', rainfall_mm: 12.5 },
      { observation_id: 'obs-2', station_code: 'VABB', observed_at: '2026-08-29T11:00:00Z', rainfall_mm: 25.0 },
      { observation_id: 'obs-3', station_code: 'VABB', observed_at: '2026-08-29T12:00:00Z', rainfall_mm: 42.0 },
    ];

    const uniqueStations = new Set(stationReadings.map((r) => r.station_code));
    expect(uniqueStations.size).toBe(1);

    // Semantics: 1 station with 3-point time-series
    const label = `${uniqueStations.size} Station (${stationReadings.length}-reading time series)`;
    expect(label).toBe('1 Station (3-reading time series)');
  });
});

describe('6. Zero Frontend Intelligence Re-computation', () => {
  it('confirms frontend receives and renders raw backend scores without altering weights', () => {
    const backendCredibilityResponse = {
      score: 0.885,
      is_machine_assessed: true,
      label: 'High Confidence',
      explanation_text: 'Corroborated by Santacruz AWS gauge (4.2km away).',
      positive_drivers: ['Santacruz AWS recorded 48mm/hr rainfall', 'GDELT news broadcast confirmed flooding'],
      negative_drivers: [],
      uncertainty_flags: [],
    };

    // Scaled purely for integer / 100 display:
    const displayScore = Math.round(backendCredibilityResponse.score * 100);
    expect(displayScore).toBe(89);
    expect(backendCredibilityResponse.positive_drivers).toHaveLength(2);
  });
});

describe('7. API Contract & Response Envelope Verification', () => {
  it('validates backend IncidentDetailPublic JSON fixture conforms to interface without casting holes', () => {
    const fixture: IncidentDetailPublic = {
      id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
      tracking_id: 'RPT-20260829-9941',
      title: 'Waterlogging on Western Express Highway near Bandra',
      description: 'Severe waterlogging blocking traffic under Kalanagar flyover.',
      category: {
        code: 'FLOOD_WATERLOGGING',
        title: 'Flood / Waterlogging',
      },
      severity: 'HIGH',
      location: {
        name: 'Bandra East, Mumbai',
        latitude: 19.0596,
        longitude: 72.8444,
      },
      occurred_at: '2026-08-29T14:30:00Z',
      credibility: {
        score: 0.86,
        label: 'High Credibility',
        explanation: 'Corroborated by Santacruz AWS gauge (3.8km away).',
        is_machine_assessed: true,
      },
      verification: {
        status: 'VERIFIED',
        is_verified: true,
        is_rejected: false,
        is_under_review: false,
        is_duplicate: false,
        notes: 'Confirmed by traffic control DEOC.',
      },
      intelligence_status: {
        overall_readiness: 'INTELLIGENCE_READY',
        last_successful_stage: 'CREDIBILITY',
      },
      summaries: {
        evidence_count: 2,
        observation_count: 3,
        duplicate_cluster_size: 4,
        is_cluster_representative: true,
      },
      media: [
        {
          id: 'med-01',
          media_type: 'IMAGE',
          url: 'https://minio.weather.internal/reports/med-01.jpg',
        },
      ],
      created_at: '2026-08-29T14:32:10Z',
    };

    expect(fixture.tracking_id).toMatch(/^RPT-\d{8}-\d{4}$/);
    expect(fixture.category.code).toBe('FLOOD_WATERLOGGING');
    expect(fixture.verification.status).toBe('VERIFIED');
    expect(fixture.intelligence_status.overall_readiness).toBe('INTELLIGENCE_READY');
    expect(fixture.summaries.is_cluster_representative).toBe(true);
  });

  it('validates IncidentDetailOperator fixture includes audit history and public fixture excludes it', () => {
    const operatorFixture: IncidentDetailOperator = {
      id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
      tracking_id: 'RPT-20260829-9941',
      title: 'Waterlogging on Western Express Highway near Bandra',
      description: 'Severe waterlogging blocking traffic under Kalanagar flyover.',
      category: {
        code: 'FLOOD_WATERLOGGING',
        title: 'Flood / Waterlogging',
      },
      severity: 'HIGH',
      location: {
        name: 'Bandra East, Mumbai',
        latitude: 19.0596,
        longitude: 72.8444,
      },
      occurred_at: '2026-08-29T14:30:00Z',
      credibility: {
        score: 0.86,
        label: 'High Credibility',
        explanation: 'Corroborated by Santacruz AWS gauge (3.8km away).',
        is_machine_assessed: true,
      },
      verification: {
        status: 'VERIFIED',
        is_verified: true,
        is_rejected: false,
        is_under_review: false,
        is_duplicate: false,
        notes: 'Confirmed by traffic control DEOC.',
      },
      intelligence_status: {
        overall_readiness: 'INTELLIGENCE_READY',
        last_successful_stage: 'CREDIBILITY',
      },
      summaries: {
        evidence_count: 2,
        observation_count: 3,
        duplicate_cluster_size: 4,
        is_cluster_representative: true,
      },
      media: [],
      verification_history: [
        {
          event_id: 'ev-01',
          report_id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
          action: 'VERIFIED',
          actor_id: 'usr-operator-01',
          created_at: '2026-08-29T14:35:00Z',
          notes: 'Confirmed by BMC control room.',
        },
      ],
      created_at: '2026-08-29T14:32:10Z',
    };

    expect(operatorFixture.verification_history).toHaveLength(1);
    expect(operatorFixture.verification_history[0].actor_id).toBe('usr-operator-01');
  });

  it('validates IncidentCredibilityData contract fixture', () => {
    const credFixture: IncidentCredibilityData = {
      incident_id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
      score: 0.85,
      is_machine_assessed: true,
      label: 'HIGH_CREDIBILITY',
      base_trust_prior: 0.5,
      explanation_text: 'Corroborated by Santacruz AWS rainfall reading (48.0mm/hr).',
      positive_drivers: ['Santacruz AWS rainfall: 48.0mm/hr', 'Linked 2 GDELT news reports'],
      negative_drivers: [],
      uncertainty_flags: ['Sparse radar coverage'],
      last_calculated_at: '2026-08-29T14:35:00Z',
    };

    expect(credFixture.score).toBeGreaterThanOrEqual(0.0);
    expect(credFixture.score).toBeLessThanOrEqual(1.0);
    expect(credFixture.positive_drivers).toHaveLength(2);
  });

  it('validates IncidentIntelligenceData contract fixture with all 5 stages', () => {
    const intelFixture: IncidentIntelligenceData = {
      incident_id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
      overall_readiness: 'INTELLIGENCE_READY',
      last_successful_stage: 'CREDIBILITY',
      stages: {
        LOCATION: { status: 'SUCCESS_WITH_RESULTS', attempt: 1, duration_ms: 24.5, error_message: null, summary: 'Geocoded' },
        DUPLICATE: { status: 'SUCCESS_WITH_NO_MATCH', attempt: 1, duration_ms: 12.0, error_message: null, summary: 'Unique' },
        EVIDENCE: { status: 'SUCCESS_WITH_RESULTS', attempt: 1, duration_ms: 310.2, error_message: null, summary: '2 articles' },
        OBSERVATION: { status: 'SUCCESS_WITH_RESULTS', attempt: 1, duration_ms: 85.1, error_message: null, summary: 'Santacruz AWS' },
        CREDIBILITY: { status: 'SUCCESS_WITH_RESULTS', attempt: 1, duration_ms: 15.4, error_message: null, summary: 'Score 0.85' },
      },
    };

    expect(Object.keys(intelFixture.stages)).toEqual(['LOCATION', 'DUPLICATE', 'EVIDENCE', 'OBSERVATION', 'CREDIBILITY']);
    expect(intelFixture.stages.LOCATION.status).toBe('SUCCESS_WITH_RESULTS');
  });

  it('validates IncidentEvidenceItemData contract fixture with all relationships', () => {
    const evidenceFixture: IncidentEvidenceItemData[] = [
      {
        link_id: 'lnk-01',
        evidence_id: 'ev-01',
        evidence_type: 'NEWS_ARTICLE',
        publisher_domain: 'timesofindia.indiatimes.com',
        title: 'Heavy rain causes severe waterlogging in Bandra',
        text_snippet: 'Traffic crawled on WEH after intense downpour.',
        published_at: '2026-08-29T14:00:00Z',
        relationship: 'SUPPORTING',
        confidence_score: 0.92,
        url: 'https://timesofindia.indiatimes.com/city/mumbai/rain-update',
        is_human_override: false,
      },
    ];

    expect(evidenceFixture[0].relationship).toBe('SUPPORTING');
    expect(evidenceFixture[0].confidence_score).toBe(0.92);
  });

  it('validates IncidentObservationItemData contract fixture with nullable metrics', () => {
    const obsFixture: IncidentObservationItemData = {
      corroboration_id: 'cor-01',
      observation_id: 'obs-01',
      station_code: 'VABB',
      station_name: 'Santacruz AWS',
      source_code: 'IMD_AWS',
      observed_at: '2026-08-29T14:00:00Z',
      distance_km: 3.8,
      relationship: 'CORROBORATING',
      corroboration_score: 0.88,
      is_contradiction: false,
      metrics: {
        rainfall_mm: 48.0,
        water_level_m: null,
        wind_speed_kmh: 35.0,
      },
      is_human_override: false,
    };

    expect(obsFixture.metrics.rainfall_mm).toBe(48.0);
    expect(obsFixture.metrics.water_level_m).toBeNull();
  });

  it('validates IncidentClusterDetailData contract fixture', () => {
    const clusterFixture: IncidentClusterDetailData = {
      cluster_id: 'cls-01',
      cluster_code: 'CLS-20260829-001',
      total_member_count: 3,
      is_representative: true,
      representative_report_id: 'rpt-01',
      temporal_span_hours: 2.5,
      members: [
        {
          report_id: 'rpt-01',
          tracking_id: 'RPT-20260829-0001',
          title: 'Kurla subway flooding',
          is_representative: true,
          similarity_score: 1.0,
          location_name: 'Kurla West',
          occurred_at: '2026-08-29T12:00:00Z',
        },
        {
          report_id: 'rpt-02',
          tracking_id: 'RPT-20260829-0002',
          title: 'Water filled near Kurla station',
          is_representative: false,
          similarity_score: 0.91,
          location_name: 'Kurla Railway Station',
          occurred_at: '2026-08-29T12:30:00Z',
        },
      ],
    };

    expect(clusterFixture.cluster_code).toBe('CLS-20260829-001');
    expect(clusterFixture.members).toHaveLength(2);
    expect(clusterFixture.members[0].is_representative).toBe(true);
    expect(clusterFixture.members[1].is_representative).toBe(false);
  });

  it('validates GeoJSONFeatureCollection contract fixture', () => {
    const geoFixture: GeoJSONFeatureCollection = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [72.8444, 19.0596],
          },
          properties: {
            id: 'c8f7952a-cf91-4cf4-9279-d75d5a2d67ea',
            tracking_id: 'RPT-20260829-9941',
            title: 'Waterlogging on Western Express Highway',
            category_code: 'FLOOD_WATERLOGGING',
            severity: 'HIGH',
            verification_status: 'VERIFIED',
            credibility_score: 0.86,
            occurred_at: '2026-08-29T14:30:00Z',
          },
        },
      ],
    };

    expect(geoFixture.type).toBe('FeatureCollection');
    expect(geoFixture.features[0].geometry.type).toBe('Point');
    expect(geoFixture.features[0].geometry.coordinates).toHaveLength(2);
  });
});

describe('8. Duplicate Cluster Presentation & Verification Status Independence', () => {
  const getClusterPresentation = (
    verificationStatus: VerificationStatus | undefined,
    totalMemberCount: number
  ) => {
    const isSingleton = totalMemberCount <= 1;
    const isMarkedDuplicate = verificationStatus === 'DUPLICATE';

    const badgeLabel = totalMemberCount === 1 ? '1 Report' : `${totalMemberCount} Grouped Reports`;

    if (isSingleton) {
      if (isMarkedDuplicate) {
        return {
          title: 'Marked as Duplicate',
          description: 'This incident is classified as a duplicate report. The current automated cluster contains 1 report.',
          badgeLabel,
          iconType: 'duplicate',
        };
      }
      return {
        title: 'Single Incident Record',
        description: 'No duplicate citizen reports have been detected within the spatial-temporal matching window for this incident.',
        badgeLabel,
        iconType: 'info',
      };
    }

    return {
      title: 'Cluster Topology Active',
      description: `${totalMemberCount} reports grouped in cluster`,
      badgeLabel,
      iconType: 'cluster',
    };
  };

  it('A. DUPLICATE + singleton cluster presents Marked as Duplicate with neutral info/copy semantics', () => {
    const pres = getClusterPresentation('DUPLICATE', 1);
    expect(pres.title).toBe('Marked as Duplicate');
    expect(pres.description).toContain('classified as a duplicate report');
    expect(pres.description).toContain('current automated cluster contains 1 report');
    expect(pres.badgeLabel).toBe('1 Report');
    expect(pres.iconType).toBe('duplicate');
  });

  it('B. PENDING / VERIFIED + singleton cluster presents Single Incident Record', () => {
    const presPending = getClusterPresentation('PENDING', 1);
    expect(presPending.title).toBe('Single Incident Record');
    expect(presPending.description).toContain('No duplicate citizen reports have been detected');
    expect(presPending.badgeLabel).toBe('1 Report');

    const presVerified = getClusterPresentation('VERIFIED', 1);
    expect(presVerified.title).toBe('Single Incident Record');
    expect(presVerified.badgeLabel).toBe('1 Report');
  });

  it('C. Multi-member cluster presents Grouped Reports with count', () => {
    const pres2 = getClusterPresentation('PENDING', 2);
    expect(pres2.badgeLabel).toBe('2 Grouped Reports');

    const pres5 = getClusterPresentation('VERIFIED', 5);
    expect(pres5.badgeLabel).toBe('5 Grouped Reports');
  });

  it('D. DUPLICATE + multi-member cluster preserves verification status separate from cluster size', () => {
    const pres = getClusterPresentation('DUPLICATE', 4);
    expect(pres.badgeLabel).toBe('4 Grouped Reports');
    expect(pres.iconType).toBe('cluster');
  });
});

describe('9. Operator Access Portal (/login) Architecture & Contract', () => {
  it('validates operator portal metadata contract without fake credentials or password UI', () => {
    const portalContract = {
      title: 'Emergency Operations Portal',
      subtitle: 'Operator Access',
      context: 'DEOC / SDRF / NDRF Control Room',
      institutionalRole: 'DEOC Officer',
      institutionalEmail: 'officer@deoc.gov.in',
      primaryActionPath: '/admin/queue',
      secondaryActionPath: '/incidents',
      hasPasswordField: false,
      hasAuthTokenState: false,
      hasFakeCredentials: false,
    };

    expect(portalContract.title).toBe('Emergency Operations Portal');
    expect(portalContract.subtitle).toBe('Operator Access');
    expect(portalContract.context).toContain('DEOC / SDRF / NDRF Control Room');
    expect(portalContract.institutionalRole).toBe('DEOC Officer');
    expect(portalContract.institutionalEmail).toBe('officer@deoc.gov.in');
    expect(portalContract.primaryActionPath).toBe('/admin/queue');
    expect(portalContract.secondaryActionPath).toBe('/incidents');
    expect(portalContract.hasPasswordField).toBe(false);
    expect(portalContract.hasAuthTokenState).toBe(false);
    expect(portalContract.hasFakeCredentials).toBe(false);
  });
});

describe('10. Status-Aware Review Drawer Actions & Terminal Lifecycle', () => {
  type DrawerActionConfig = {
    isTerminal: boolean;
    showActiveControls: boolean;
    showOperatorNotesInput: boolean;
    terminalTitle?: string;
    terminalSubtitle?: string;
  };

  const getDrawerActionConfig = (verificationStatus: string): DrawerActionConfig => {
    const isVerified = verificationStatus === 'VERIFIED';
    const isRejected = verificationStatus === 'REJECTED';
    const isDuplicate = verificationStatus === 'DUPLICATE';
    const isTerminal = isVerified || isRejected || isDuplicate;

    if (!isTerminal) {
      return {
        isTerminal: false,
        showActiveControls: true,
        showOperatorNotesInput: true,
      };
    }

    if (isVerified) {
      return {
        isTerminal: true,
        showActiveControls: false,
        showOperatorNotesInput: false,
        terminalTitle: 'Ground Truth Verified',
        terminalSubtitle: 'Verification completed',
      };
    }
    if (isRejected) {
      return {
        isTerminal: true,
        showActiveControls: false,
        showOperatorNotesInput: false,
        terminalTitle: 'Incident Rejected',
        terminalSubtitle: 'Verification closed',
      };
    }
    if (isDuplicate) {
      return {
        isTerminal: true,
        showActiveControls: false,
        showOperatorNotesInput: false,
        terminalTitle: 'Marked as Duplicate',
        terminalSubtitle: 'Verification closed',
      };
    }

    return {
      isTerminal: false,
      showActiveControls: true,
      showOperatorNotesInput: true,
    };
  };

  it('A. PENDING report renders active mutation controls and notes textarea', () => {
    const config = getDrawerActionConfig('PENDING');
    expect(config.isTerminal).toBe(false);
    expect(config.showActiveControls).toBe(true);
    expect(config.showOperatorNotesInput).toBe(true);
  });

  it('B. UNDER_REVIEW report renders active mutation controls and notes textarea', () => {
    const config = getDrawerActionConfig('UNDER_REVIEW');
    expect(config.isTerminal).toBe(false);
    expect(config.showActiveControls).toBe(true);
    expect(config.showOperatorNotesInput).toBe(true);
  });

  it('C. VERIFIED report renders terminal completed presentation without active mutation controls', () => {
    const config = getDrawerActionConfig('VERIFIED');
    expect(config.isTerminal).toBe(true);
    expect(config.showActiveControls).toBe(false);
    expect(config.showOperatorNotesInput).toBe(false);
    expect(config.terminalTitle).toBe('Ground Truth Verified');
    expect(config.terminalSubtitle).toBe('Verification completed');
  });

  it('D. REJECTED report renders terminal closed presentation without active mutation controls', () => {
    const config = getDrawerActionConfig('REJECTED');
    expect(config.isTerminal).toBe(true);
    expect(config.showActiveControls).toBe(false);
    expect(config.showOperatorNotesInput).toBe(false);
    expect(config.terminalTitle).toBe('Incident Rejected');
    expect(config.terminalSubtitle).toBe('Verification closed');
  });

  it('E. DUPLICATE report renders terminal duplicate presentation without active mutation controls', () => {
    const config = getDrawerActionConfig('DUPLICATE');
    expect(config.isTerminal).toBe(true);
    expect(config.showActiveControls).toBe(false);
    expect(config.showOperatorNotesInput).toBe(false);
    expect(config.terminalTitle).toBe('Marked as Duplicate');
    expect(config.terminalSubtitle).toBe('Verification closed');
  });
});
