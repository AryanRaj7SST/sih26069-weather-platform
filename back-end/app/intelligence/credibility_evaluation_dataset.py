"""Synthetic Credibility Benchmark Dataset (60 Cases).

Label: Synthetic Credibility Benchmark Only
(No claim of real-world probability calibration).

Validates:
1. Baseline Priors & Metadata Completeness (Cases 1–10)
2. Crowd Cluster & Duplicate Saturation (Cases 11–20)
3. Digital Evidence & Syndication Resistance (Cases 21–30)
4. Physical Sensor Observations & Station Collapse (Cases 31–40)
5. Cross-Family Multi-Source Diversity Multipliers (Cases 41–50)
6. Adversarial, Contradictions, & Invariant Properties (Cases 51–60)
"""

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.intelligence.credibility_scorer import CredibilityScorer, credibility_scorer
from app.intelligence.schemas import (
    ContradictionInput,
    DigitalEvidenceGroupInput,
    IncidentCredibilityInputs,
    PhysicalStationInput,
    SourceFamily,
)


@dataclass
class BenchmarkTestCase:
    """A synthetic test incident with input parameters and expected properties."""

    case_id: int
    suite: str
    name: str
    description: str
    inputs: IncidentCredibilityInputs
    expected_min_score: float
    expected_max_score: float
    expected_cap: float


def generate_benchmark_dataset() -> List[BenchmarkTestCase]:
    """Construct the canonical 60-case synthetic credibility benchmark suite."""
    cases: List[BenchmarkTestCase] = []

    # =========================================================================
    # SUITE 1: Baseline Priors & Metadata Completeness (Cases 1–10)
    # =========================================================================
    cases.append(
        BenchmarkTestCase(
            case_id=1,
            suite="1. Baseline Priors & Metadata",
            name="Standard Citizen Report",
            description="Isolated citizen report with complete metadata.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.595,
            expected_max_score=0.605,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=2,
            suite="1. Baseline Priors & Metadata",
            name="Official IMD AWS Report",
            description="Isolated IMD automated weather station alert.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="IMD_AWS",
                source_type="IMD",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.875,
            expected_max_score=0.885,
            expected_cap=0.88,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=3,
            suite="1. Baseline Priors & Metadata",
            name="Official NDMA SACHET Alert",
            description="High-trust NDMA national disaster alert bulletin.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="NDMA_SACHET",
                source_type="GOVERNMENT_PORTAL",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.875,
            expected_max_score=0.885,
            expected_cap=0.88,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=4,
            suite="1. Baseline Priors & Metadata",
            name="Verified NGO Partner Report",
            description="Pre-verified disaster response NGO partner.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="NGO_RESCUE",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.75,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.645,
            expected_max_score=0.655,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=5,
            suite="1. Baseline Priors & Metadata",
            name="Anonymous Untrusted Citizen",
            description="Anonymous citizen submission with low baseline prior.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_ANON",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.40,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.395,
            expected_max_score=0.405,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=6,
            suite="1. Baseline Priors & Metadata",
            name="Citizen Missing Coordinates",
            description="Citizen report lacking GPS coordinates (quality=0.70).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=False,
                has_timestamp=True,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.540,
            expected_max_score=0.550,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=7,
            suite="1. Baseline Priors & Metadata",
            name="Citizen Missing Timestamp",
            description="Citizen report lacking exact timestamp (quality=0.75).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=False,
                has_location_name=True,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.550,
            expected_max_score=0.560,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=8,
            suite="1. Baseline Priors & Metadata",
            name="Citizen Missing Description",
            description="Citizen report lacking text description (quality=0.85).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=True,
                has_description=False,
                has_category=True,
            ),
            expected_min_score=0.570,
            expected_max_score=0.580,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=9,
            suite="1. Baseline Priors & Metadata",
            name="Citizen Missing Location Name",
            description="Citizen report lacking location name text (quality=0.80).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                has_coordinates=True,
                has_timestamp=True,
                has_location_name=False,
                has_description=True,
                has_category=True,
            ),
            expected_min_score=0.560,
            expected_max_score=0.570,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=10,
            suite="1. Baseline Priors & Metadata",
            name="High-Trust Official with Minimal Fields",
            description="Official source with missing coords and text (quality=0.30).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="IMD_AWS",
                source_type="IMD",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                has_coordinates=False,
                has_timestamp=True,
                has_location_name=False,
                has_description=False,
                has_category=False,
            ),
            expected_min_score=0.690,
            expected_max_score=0.705,
            expected_cap=0.88,
        )
    )

    # =========================================================================
    # SUITE 2: Crowd & Duplicate Repetition Saturation (Cases 11–20)
    # =========================================================================
    for k_val, cid in zip([2, 3, 4, 5, 6, 8, 10, 15, 20, 50], range(11, 21)):
        cases.append(
            BenchmarkTestCase(
                case_id=cid,
                suite="2. Crowd & Duplicate Saturation",
                name=f"Duplicate Cluster with {k_val} Reports",
                description=f"Citizen report backed by {k_val} duplicate cluster members.",
                inputs=IncidentCredibilityInputs(
                    incident_id=uuid.uuid4(),
                    source_code="CITIZEN_WEB",
                    source_type="CITIZEN_REPORT",
                    source_base_trust=0.60,
                    origin_family=SourceFamily.CITIZEN,
                    has_coordinates=True,
                    has_timestamp=True,
                    has_location_name=True,
                    has_description=True,
                    has_category=True,
                    cluster_member_count=k_val,
                ),
                expected_min_score=0.620,
                expected_max_score=0.725,
                expected_cap=0.82,
            )
        )

    # =========================================================================
    # SUITE 3: Digital Evidence & Syndication Resistance (Cases 21–30)
    # =========================================================================
    cases.append(
        BenchmarkTestCase(
            case_id=21,
            suite="3. Digital Evidence & Syndication",
            name="1 Supporting News Article",
            description="Citizen report linked to 1 independent supporting news article.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    )
                ],
            ),
            expected_min_score=0.680,
            expected_max_score=0.690,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=22,
            suite="3. Digital Evidence & Syndication",
            name="1 Related News Article",
            description="Citizen report linked to 1 related contextual article (role=0.35).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=0.35,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    )
                ],
            ),
            expected_min_score=0.625,
            expected_max_score=0.635,
            expected_cap=0.98,
        )
    )

    for m_val, cid in zip([2, 5, 10, 20], [23, 24, 25, 26]):
        cases.append(
            BenchmarkTestCase(
                case_id=cid,
                suite="3. Digital Evidence & Syndication",
                name=f"{m_val} Syndicated Articles from 1 Domain",
                description=(
                    f"Citizen report linked to {m_val} articles from the same publisher domain."
                ),
                inputs=IncidentCredibilityInputs(
                    incident_id=uuid.uuid4(),
                    source_code="CITIZEN_WEB",
                    source_type="CITIZEN_REPORT",
                    source_base_trust=0.60,
                    origin_family=SourceFamily.CITIZEN,
                    evidence_groups=[
                        DigitalEvidenceGroupInput(
                            provenance_key="domain_timesofindia.com",
                            max_confidence=0.80,
                            role_weight=1.0,
                            article_count=m_val,
                            source_family=SourceFamily.NEWS,
                        )
                    ],
                ),
                expected_min_score=0.690,
                expected_max_score=0.710,
                expected_cap=0.98,
            )
        )

    cases.append(
        BenchmarkTestCase(
            case_id=27,
            suite="3. Digital Evidence & Syndication",
            name="2 Independent News Domains",
            description="Citizen report linked to 2 distinct news publisher domains.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_ndtv.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                ],
            ),
            expected_min_score=0.730,
            expected_max_score=0.740,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=28,
            suite="3. Digital Evidence & Syndication",
            name="3 Independent News Domains",
            description="Citizen report linked to 3 distinct news publisher domains.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key=f"domain_{d}.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    )
                    for d in ["thehindu", "ndtv", "indianexpress"]
                ],
            ),
            expected_min_score=0.765,
            expected_max_score=0.775,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=29,
            suite="3. Digital Evidence & Syndication",
            name="5 Independent News Domains",
            description="Citizen report linked to 5 distinct news publisher domains.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key=f"domain_{d}.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    )
                    for d in ["thehindu", "ndtv", "indianexpress", "hindustantimes", "deccanherald"]
                ],
            ),
            expected_min_score=0.790,
            expected_max_score=0.800,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=30,
            suite="3. Digital Evidence & Syndication",
            name="Exact Duplicate Content Hashing",
            description="10 identical wire reprints matching Level 1 SHA256 hash.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="hash_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=10,
                        source_family=SourceFamily.NEWS,
                    )
                ],
            ),
            expected_min_score=0.700,
            expected_max_score=0.710,
            expected_cap=0.98,
        )
    )

    # =========================================================================
    # SUITE 4: Physical Sensor Telemetry & Station Collapse (Cases 31–40)
    # =========================================================================
    cases.append(
        BenchmarkTestCase(
            case_id=31,
            suite="4. Physical Sensor Telemetry",
            name="Single CWC Gauge Reading",
            description="Citizen report corroborated by 1 single point observation.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_01",
                        corroboration_score=0.60,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=1,
                    )
                ],
            ),
            expected_min_score=0.670,
            expected_max_score=0.680,
            expected_cap=0.85,
        )
    )

    for pts, sc, cid in zip([3, 6, 12, 24], [0.70, 0.78, 0.82, 0.85], [32, 33, 34, 35]):
        cases.append(
            BenchmarkTestCase(
                case_id=cid,
                suite="4. Physical Sensor Telemetry",
                name=f"CWC Station with {pts}-Point Time Series",
                description=(
                    "Sequential gauge readings over time strengthening "
                    f"trend assessment to {sc:.2f}."
                ),
                inputs=IncidentCredibilityInputs(
                    incident_id=uuid.uuid4(),
                    source_code="CITIZEN_WEB",
                    source_type="CITIZEN_REPORT",
                    source_base_trust=0.60,
                    origin_family=SourceFamily.CITIZEN,
                    observation_stations=[
                        PhysicalStationInput(
                            station_key="cwc_station_bhad_01",
                            corroboration_score=sc,
                            relationship_weight=1.0,
                            source_family=SourceFamily.SENSOR,
                            points_count=pts,
                        )
                    ],
                ),
                expected_min_score=0.685,
                expected_max_score=0.715,
                expected_cap=0.85,
            )
        )

    cases.append(
        BenchmarkTestCase(
            case_id=36,
            suite="4. Physical Sensor Telemetry",
            name="CWC Steady Trend",
            description="Gauge trend is steady (relationship=0.50).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_01",
                        corroboration_score=0.60,
                        relationship_weight=0.50,
                        source_family=SourceFamily.SENSOR,
                        points_count=12,
                    )
                ],
            ),
            expected_min_score=0.635,
            expected_max_score=0.645,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=37,
            suite="4. Physical Sensor Telemetry",
            name="CWC Falling Trend Weak Match",
            description="Gauge trend is falling (relationship=0.20).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_01",
                        corroboration_score=0.60,
                        relationship_weight=0.20,
                        source_family=SourceFamily.SENSOR,
                        points_count=12,
                    )
                ],
            ),
            expected_min_score=0.610,
            expected_max_score=0.620,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=38,
            suite="4. Physical Sensor Telemetry",
            name="2 Independent CWC Stations",
            description="Citizen report corroborated by 2 upstream/downstream CWC stations.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    ),
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_02",
                        corroboration_score=0.75,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    ),
                ],
            ),
            expected_min_score=0.750,
            expected_max_score=0.760,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=39,
            suite="4. Physical Sensor Telemetry",
            name="3 Independent CWC Stations",
            description="Citizen report corroborated by 3 distinct CWC stations in basin.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key=f"cwc_station_bhad_0{idx}",
                        corroboration_score=sc,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                    for idx, sc in [(1, 0.85), (2, 0.75), (3, 0.70)]
                ],
            ),
            expected_min_score=0.770,
            expected_max_score=0.785,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=40,
            suite="4. Physical Sensor Telemetry",
            name="CWC Gauge + IMD AWS Rain Gauge (2 Physical Families)",
            description="CWC river gauge + IMD automatic weather rain gauge.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_station_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    ),
                    PhysicalStationInput(
                        station_key="imd_aws_station_01",
                        corroboration_score=0.80,
                        relationship_weight=1.0,
                        source_family=SourceFamily.OFFICIAL,
                        points_count=24,
                    ),
                ],
            ),
            expected_min_score=0.760,
            expected_max_score=0.770,
            expected_cap=0.98,
        )
    )

    # =========================================================================
    # SUITE 5: Cross-Family Multi-Source Diversity (Cases 41–50)
    # =========================================================================
    cases.append(
        BenchmarkTestCase(
            case_id=41,
            suite="5. Multi-Source Diversity",
            name="Citizen + Official Alert (2 Families)",
            description="Citizen report linked to supporting official NDMA alert.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="official_ndma_bulletin",
                        max_confidence=0.90,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.OFFICIAL,
                    )
                ],
            ),
            expected_min_score=0.690,
            expected_max_score=0.700,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=42,
            suite="5. Multi-Source Diversity",
            name="Citizen + CWC Telemetry (2 Families)",
            description="Citizen report corroborated by CWC telemetry.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
            ),
            expected_min_score=0.705,
            expected_max_score=0.715,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=43,
            suite="5. Multi-Source Diversity",
            name="Citizen + News Article (2 Families)",
            description="Citizen report backed by 1 independent news report.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    )
                ],
            ),
            expected_min_score=0.680,
            expected_max_score=0.690,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=44,
            suite="5. Multi-Source Diversity",
            name="Citizen + Mastodon Post (2 Families)",
            description="Citizen report backed by 1 Mastodon social verification.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="mastodon_instance_india",
                        max_confidence=0.60,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.SOCIAL,
                    )
                ],
            ),
            expected_min_score=0.655,
            expected_max_score=0.665,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=45,
            suite="5. Multi-Source Diversity",
            name="Citizen + CWC + 2 News (3 Families)",
            description="Citizen report backed by CWC gauge and 2 independent news publishers.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_ndtv.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                ],
            ),
            expected_min_score=0.850,
            expected_max_score=0.865,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=46,
            suite="5. Multi-Source Diversity",
            name="Citizen + CWC + Official Alert (3 Families)",
            description="Citizen report backed by CWC gauge and NDMA official bulletin.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="official_ndma_alert",
                        max_confidence=0.85,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.OFFICIAL,
                    )
                ],
            ),
            expected_min_score=0.805,
            expected_max_score=0.815,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=47,
            suite="5. Multi-Source Diversity",
            name="Citizen + CWC + News + Official (4 Families)",
            description="Citizen report corroborated across 4 independent families.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="official_ndma_alert",
                        max_confidence=0.85,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.OFFICIAL,
                    ),
                ],
            ),
            expected_min_score=0.870,
            expected_max_score=0.880,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=48,
            suite="5. Multi-Source Diversity",
            name="Full 5-Family Multi-Source Corroboration",
            description="Citizen + Official + News + Social + Sensor confirmation.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="official_ndma_alert",
                        max_confidence=0.85,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.OFFICIAL,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="mastodon_social_post",
                        max_confidence=0.75,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.SOCIAL,
                    ),
                ],
            ),
            expected_min_score=0.915,
            expected_max_score=0.925,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=49,
            suite="5. Multi-Source Diversity",
            name="Cross-Quoted Media Defense",
            description="News article merely quotes social post (lineage shared, no 2nd family).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_quoting_mastodon",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                        is_derived_lineage=True,
                    )
                ],
            ),
            expected_min_score=0.675,
            expected_max_score=0.685,
            expected_cap=0.82,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=50,
            suite="5. Multi-Source Diversity",
            name="Official Report + Full Physical & News Corroboration",
            description="IMD AWS report confirmed by CWC telemetry and independent news.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="IMD_AWS",
                source_type="IMD",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_ndtv.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                ],
            ),
            expected_min_score=0.950,
            expected_max_score=0.970,
            expected_cap=0.98,
        )
    )

    # =========================================================================
    # SUITE 6: Adversarial, Contradictions, & Invariants (Cases 51–60)
    # =========================================================================
    cases.append(
        BenchmarkTestCase(
            case_id=51,
            suite="6. Adversarial & Contradictions",
            name="Diagnostic Physical Gauge Contradiction",
            description="Citizen report with diagnostic receding gauge contradiction.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                negative_contradictions=[
                    ContradictionInput(
                        signal_source_key="cwc_gauge_contradiction",
                        contradiction_score=0.90,
                        is_diagnostic=True,
                        is_physical_sensor=True,
                    )
                ],
            ),
            expected_min_score=0.325,
            expected_max_score=0.335,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=52,
            suite="6. Adversarial & Contradictions",
            name="Official Report with Diagnostic Physical Conflict",
            description="Official report contradicted by direct physical sensor readings.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="IMD_AWS",
                source_type="IMD",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                negative_contradictions=[
                    ContradictionInput(
                        signal_source_key="cwc_gauge_contradiction",
                        contradiction_score=0.90,
                        is_diagnostic=True,
                        is_physical_sensor=True,
                    )
                ],
            ),
            expected_min_score=0.625,
            expected_max_score=0.635,
            expected_cap=0.88,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=53,
            suite="6. Adversarial & Contradictions",
            name="Crowd Cluster with Contradictory Sensor",
            description="5 duplicate citizen reports contradicted by physical telemetry.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                cluster_member_count=5,
                negative_contradictions=[
                    ContradictionInput(
                        signal_source_key="cwc_gauge_contradiction",
                        contradiction_score=0.90,
                        is_diagnostic=True,
                        is_physical_sensor=True,
                    )
                ],
            ),
            expected_min_score=0.410,
            expected_max_score=0.425,
            expected_cap=0.82,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=54,
            suite="6. Adversarial & Contradictions",
            name="Weak Observation Neutrality",
            description="Weak correlation (relationship=0.20) gives 0 penalty.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_weak_station",
                        corroboration_score=0.70,
                        relationship_weight=0.20,
                        source_family=SourceFamily.SENSOR,
                    )
                ],
            ),
            expected_min_score=0.615,
            expected_max_score=0.625,
            expected_cap=0.85,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=55,
            suite="6. Adversarial & Contradictions",
            name="Missing Data Neutrality",
            description="Absence of sensor data produces 0 penalty (score=0.6000).",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
            ),
            expected_min_score=0.595,
            expected_max_score=0.605,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=56,
            suite="6. Adversarial & Contradictions",
            name="Repeated Contradiction Penalty Saturation",
            description="10 duplicate debunking articles collapse to bounded max penalty.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                negative_contradictions=[
                    ContradictionInput(
                        signal_source_key=f"debunking_article_{idx}",
                        contradiction_score=0.85,
                        is_diagnostic=True,
                        is_physical_sensor=False,
                    )
                    for idx in range(10)
                ],
            ),
            expected_min_score=0.100,
            expected_max_score=0.110,
            expected_cap=0.65,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=57,
            suite="6. Adversarial & Contradictions",
            name="Official Source with Wrong Coordinates",
            description="Official bulletin lacking precise coordinates.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="IMD_AWS",
                source_type="IMD",
                source_base_trust=0.90,
                origin_family=SourceFamily.OFFICIAL,
                has_coordinates=False,
            ),
            expected_min_score=0.815,
            expected_max_score=0.825,
            expected_cap=0.88,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=58,
            suite="6. Adversarial & Contradictions",
            name="Weak Source with Overwhelming Corroboration",
            description="Anonymous citizen report (prior 0.40) verified by CWC and 2 news domains.",
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_ANON",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.40,
                origin_family=SourceFamily.CITIZEN,
                observation_stations=[
                    PhysicalStationInput(
                        station_key="cwc_bhad_01",
                        corroboration_score=0.85,
                        relationship_weight=1.0,
                        source_family=SourceFamily.SENSOR,
                        points_count=24,
                    )
                ],
                evidence_groups=[
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_thehindu.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                    DigitalEvidenceGroupInput(
                        provenance_key="domain_ndtv.com",
                        max_confidence=0.80,
                        role_weight=1.0,
                        article_count=1,
                        source_family=SourceFamily.NEWS,
                    ),
                ],
            ),
            expected_min_score=0.780,
            expected_max_score=0.790,
            expected_cap=0.98,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=59,
            suite="6. Adversarial & Contradictions",
            name="Human VERIFIED Separation Invariant",
            description=(
                "Machine credibility score remains purely algorithmic for human-verified report."
            ),
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                cluster_member_count=3,
            ),
            expected_min_score=0.655,
            expected_max_score=0.665,
            expected_cap=0.82,
        )
    )

    cases.append(
        BenchmarkTestCase(
            case_id=60,
            suite="6. Adversarial & Contradictions",
            name="Human REJECTED Separation Invariant",
            description=(
                "Machine credibility score remains historically preserved "
                "for human-rejected report."
            ),
            inputs=IncidentCredibilityInputs(
                incident_id=uuid.uuid4(),
                source_code="CITIZEN_WEB",
                source_type="CITIZEN_REPORT",
                source_base_trust=0.60,
                origin_family=SourceFamily.CITIZEN,
                cluster_member_count=3,
            ),
            expected_min_score=0.655,
            expected_max_score=0.665,
            expected_cap=0.82,
        )
    )

    return cases


def run_synthetic_benchmark(
    scorer: Optional[CredibilityScorer] = None,
) -> Dict[str, object]:
    """Execute the full 60-case synthetic benchmark and report accuracy and invariant metrics."""
    active_scorer = scorer or credibility_scorer
    cases = generate_benchmark_dataset()

    passed_count = 0
    results: List[Dict[str, object]] = []

    for c in cases:
        signals = active_scorer.score_incident(inputs=c.inputs)
        score = signals.final_credibility_score

        is_passed = (
            c.expected_min_score <= score <= c.expected_max_score
            and signals.applied_cap == c.expected_cap
        )
        if is_passed:
            passed_count += 1

        results.append(
            {
                "case_id": c.case_id,
                "suite": c.suite,
                "name": c.name,
                "score": score,
                "expected_min": c.expected_min_score,
                "expected_max": c.expected_max_score,
                "applied_cap": signals.applied_cap,
                "expected_cap": c.expected_cap,
                "passed": is_passed,
            }
        )

    # Monotonicity checks across representative progression
    c_citizen = results[0]["score"]  # Case 1
    c_crowd5 = results[13]["score"]  # Case 14 (k=5)
    c_cwc = results[34]["score"]  # Case 35 (24-pt trend)
    c_news2 = results[26]["score"]  # Case 27 (2 news domains)
    c_full = results[44]["score"]  # Case 45 (Citizen + CWC + News)
    c_5fam = results[47]["score"]  # Case 48 (5 families)

    monotonicity_passed = bool(
        isinstance(c_citizen, (int, float))
        and isinstance(c_crowd5, (int, float))
        and isinstance(c_cwc, (int, float))
        and isinstance(c_news2, (int, float))
        and isinstance(c_full, (int, float))
        and isinstance(c_5fam, (int, float))
        and c_citizen < c_crowd5 < c_cwc < c_news2 < c_full < c_5fam
    )

    return {
        "benchmark_label": "Synthetic Credibility Benchmark Only",
        "total_cases": len(cases),
        "passed_cases": passed_count,
        "pass_rate_pct": round((passed_count / len(cases)) * 100, 2),
        "monotonicity_ordering_passed": monotonicity_passed,
        "case_results": results,
    }
