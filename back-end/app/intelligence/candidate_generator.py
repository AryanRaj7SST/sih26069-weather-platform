import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.intelligence.schemas import CandidateQueryResult
from app.models.report import WeatherReport

logger = logging.getLogger(__name__)


class CandidateGenerator:
    """Index-assisted PostGIS spatial and temporal candidate query generator."""

    def __init__(
        self,
        max_radius_meters: Optional[float] = None,
        max_window_hours: Optional[float] = None,
        default_limit: Optional[int] = None,
    ) -> None:
        self.max_radius = max_radius_meters or settings.DUPLICATE_SPATIAL_RADIUS_METERS
        self.max_window = timedelta(
            hours=(max_window_hours or settings.DUPLICATE_TIME_WINDOW_HOURS)
        )
        self.default_limit = default_limit or settings.DUPLICATE_CANDIDATE_LIMIT

    async def get_candidates(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        geom: Any,
        occurred_at: datetime,
        limit: Optional[int] = None,
    ) -> CandidateQueryResult:
        """Retrieve candidate reports using index-assisted spatial and temporal filters.

        Returns CandidateQueryResult exposing candidates, total count, and truncation indicator.
        """
        query_limit = limit or self.default_limit

        if geom is None or occurred_at is None:
            return CandidateQueryResult(
                candidates=[],
                total_found=0,
                candidate_limit=query_limit,
                is_truncated=False,
            )

        time_min = occurred_at - self.max_window
        time_max = occurred_at + self.max_window

        try:
            # Query candidates up to limit + 1 to detect truncation safely
            query = (
                select(WeatherReport)
                .where(
                    WeatherReport.id != report_id,
                    WeatherReport.occurred_at >= time_min,
                    WeatherReport.occurred_at <= time_max,
                    func.ST_DWithin(
                        cast(WeatherReport.geom, Geography),
                        cast(geom, Geography),
                        self.max_radius,
                    ),
                )
                .order_by(
                    func.ST_Distance(
                        cast(WeatherReport.geom, Geography),
                        cast(geom, Geography),
                    ).asc()
                )
                .limit(query_limit + 1)
            )

            result = await db.execute(query)
            all_fetched = list(result.scalars().all())

            is_truncated = len(all_fetched) > query_limit
            candidates = all_fetched[:query_limit]

            if is_truncated:
                logger.warning(
                    f"Candidate query for report {report_id} truncated at cap {query_limit}"
                )

            return CandidateQueryResult(
                candidates=candidates,
                total_found=len(all_fetched),
                candidate_limit=query_limit,
                is_truncated=is_truncated,
            )
        except Exception as e:
            logger.error(f"Candidate query failed for report {report_id}: {e}", exc_info=True)
            raise RuntimeError(f"Database error during candidate generation: {e}") from e


candidate_generator = CandidateGenerator()
