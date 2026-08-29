import logging
from datetime import timedelta
from typing import List, Optional

from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.intelligence.resolver import location_resolver
from app.models.evidence import EvidenceItem
from app.models.report import WeatherReport

logger = logging.getLogger(__name__)


class EvidenceCandidateGenerator:
    """Index-assisted candidate generator for EvidenceItem <-> WeatherReport matching."""

    def __init__(
        self,
        max_spatial_radius_meters: Optional[float] = None,
        max_window_hours: Optional[float] = None,
        default_limit: Optional[int] = None,
    ) -> None:
        self.max_radius = max_spatial_radius_meters or settings.EVIDENCE_SPATIAL_RADIUS_METERS
        self.max_window = timedelta(hours=(max_window_hours or settings.EVIDENCE_TIME_WINDOW_HOURS))
        self.default_limit = default_limit or settings.EVIDENCE_CANDIDATE_LIMIT

    async def get_incident_candidates_for_evidence(
        self,
        db: AsyncSession,
        evidence: EvidenceItem,
        limit: Optional[int] = None,
    ) -> tuple[List[WeatherReport], bool]:
        """Find candidate WeatherReports matching an EvidenceItem within temporal/spatial bounds."""
        query_limit = limit or self.default_limit
        pub_time = evidence.published_at or evidence.captured_at

        # Resolve location entities from evidence
        full_text = f"{evidence.title} {evidence.text_snippet or ''}".strip()
        loc_res = location_resolver.resolve(text=full_text)

        time_min = (pub_time - self.max_window) if pub_time else None
        time_max = (pub_time + self.max_window) if pub_time else None

        try:
            stmt = select(WeatherReport)

            # Temporal filter
            if time_min and time_max:
                stmt = stmt.where(
                    WeatherReport.occurred_at >= time_min,
                    WeatherReport.occurred_at <= time_max,
                )

            # Spatial filter if evidence has coordinates
            if loc_res.latitude is not None and loc_res.longitude is not None:
                point_wkt = f"SRID=4326;POINT({loc_res.longitude} {loc_res.latitude})"
                name_match = loc_res.city or loc_res.place_name
                stmt = stmt.where(
                    or_(
                        func.ST_DWithin(
                            cast(WeatherReport.geom, Geography),
                            func.ST_GeogFromText(point_wkt),
                            self.max_radius,
                        ),
                        WeatherReport.location_name.ilike(f"%{name_match}%"),
                    )
                )
            elif loc_res.city:
                stmt = stmt.where(WeatherReport.location_name.ilike(f"%{loc_res.city}%"))

            stmt = stmt.order_by(WeatherReport.occurred_at.desc()).limit(query_limit + 1)

            res = await db.execute(stmt)
            all_found = list(res.scalars().all())

            is_truncated = len(all_found) > query_limit
            candidates = all_found[:query_limit]

            if is_truncated:
                logger.warning(
                    f"Candidate query for evidence {evidence.id} truncated at cap {query_limit}"
                )

            return candidates, is_truncated
        except Exception as e:
            logger.error(
                f"Failed candidate generation for evidence {evidence.id}: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Database error during candidate retrieval: {e}") from e


evidence_candidate_generator = EvidenceCandidateGenerator()
