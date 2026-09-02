"""Production service for path corridor hazard checks using PostGIS spatial geography buffering."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from geoalchemy2 import Geometry, Geography
from geoalchemy2.functions import ST_AsGeoJSON, ST_Buffer, ST_Distance, ST_Intersects, ST_MakeLine, ST_MakePoint, ST_SetSRID
from sqlalchemy import and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import EventCategory
from app.models.report import WeatherReport
from app.schemas.route import (
    IntersectingHazardDetail,
    RouteCheckRequest,
    RouteCheckResponseData,
)

logger = logging.getLogger(__name__)


class RouteCheckService:
    """Service providing spatial path blockage and hazard corridor checks."""

    async def check_route_corridor(
        self,
        session: AsyncSession,
        payload: RouteCheckRequest,
    ) -> RouteCheckResponseData:
        """Perform PostGIS geography buffer intersection check between origin and destination."""
        orig = payload.origin
        dest = payload.destination
        corridor_km = payload.corridor_km
        corridor_meters = corridor_km * 1000.0

        # Construct 4326 PostGIS geometry line between origin and destination
        orig_point = ST_SetSRID(ST_MakePoint(orig.longitude, orig.latitude), 4326)
        dest_point = ST_SetSRID(ST_MakePoint(dest.longitude, dest.latitude), 4326)
        path_line = ST_MakeLine(orig_point, dest_point)

        # Buffer path line by corridor_meters using PostGIS geography conversion
        path_geography = cast(path_line, Geography)
        buffer_geography = ST_Buffer(path_geography, corridor_meters)
        buffer_geometry = cast(buffer_geography, Geometry)

        # Query active verified / high-credibility incidents intersecting the buffered corridor
        stmt = (
            select(
                WeatherReport,
                ST_Distance(cast(WeatherReport.geom, Geography), path_geography).label("dist_m"),
            )
            .options(selectinload(WeatherReport.category))
            .where(
                WeatherReport.geom.isnot(None),
                WeatherReport.verification_status.in_(["VERIFIED", "UNDER_REVIEW"]),
                WeatherReport.credibility_score >= 0.50,
                ST_Intersects(WeatherReport.geom, buffer_geometry),
            )
            .order_by("dist_m", WeatherReport.occurred_at.desc())
            .limit(50)
        )

        res = await session.execute(stmt)
        rows = res.all()

        intersecting_hazards: List[IntersectingHazardDetail] = []
        severity_hierarchy = {"SEVERE": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
        max_sev_rank = 0
        highest_severity: Optional[str] = None

        for report, dist_m in rows:
            cat_code = (
                report.category.category_code
                if report.category
                else (report.reported_category or "OTHER")
            )
            rank = severity_hierarchy.get(report.severity, 1)
            if rank > max_sev_rank:
                max_sev_rank = rank
                highest_severity = report.severity

            intersecting_hazards.append(
                IntersectingHazardDetail(
                    id=report.id,
                    tracking_id=report.tracking_id,
                    title=report.title,
                    category_code=cat_code,
                    severity=report.severity,
                    verification_status=report.verification_status,
                    credibility_score=report.credibility_score,
                    credibility_reason=report.credibility_reason,
                    latitude=report.latitude,
                    longitude=report.longitude,
                    location_name=report.location_name,
                    distance_to_corridor_center_m=round(float(dist_m or 0.0), 1),
                    occurred_at=report.occurred_at,
                )
            )

        # Fetch GeoJSON string representation of path and corridor buffer
        geojson_stmt = select(
            ST_AsGeoJSON(path_line).label("line_geojson"),
            ST_AsGeoJSON(buffer_geometry).label("buffer_geojson"),
        )
        g_res = await session.execute(geojson_stmt)
        g_row = g_res.one()

        import json

        line_dict = json.loads(g_row.line_geojson) if g_row.line_geojson else {}
        buffer_dict = json.loads(g_row.buffer_geojson) if g_row.buffer_geojson else {}

        path_geojson_feature = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": line_dict,
                    "properties": {
                        "type": "PATH_LINE",
                        "origin_name": orig.name or "Origin",
                        "destination_name": dest.name or "Destination",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": buffer_dict,
                    "properties": {
                        "type": "CORRIDOR_BUFFER",
                        "corridor_km": corridor_km,
                    },
                },
            ],
        }

        is_blocked = len(intersecting_hazards) > 0

        return RouteCheckResponseData(
            is_blocked=is_blocked,
            hazard_count=len(intersecting_hazards),
            corridor_km=corridor_km,
            highest_severity=highest_severity,
            intersecting_incidents=intersecting_hazards,
            path_geojson=path_geojson_feature,
        )


route_check_service = RouteCheckService()
