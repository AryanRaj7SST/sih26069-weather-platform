"""Seed script for India land and EEZ boundary polygons in india_area table.

Safe to run multiple times (idempotent via ON CONFLICT / name check).
"""

import asyncio
import json
import logging
import os
import sys
import uuid

# Add parent directory to path so 'app' package imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from geoalchemy2.elements import WKTElement
from shapely.geometry import MultiPolygon, Polygon, shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.india_area import IndiaArea

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def to_multipolygon_wkt(geom_dict: dict) -> str:
    """Convert GeoJSON geometry to MultiPolygon WKT."""
    sh = shape(geom_dict)
    if isinstance(sh, Polygon):
        sh = MultiPolygon([sh])
    elif not isinstance(sh, MultiPolygon):
        raise ValueError(f"Expected Polygon or MultiPolygon, got {sh.geom_type}")
    return sh.wkt


async def seed_india_area(session: AsyncSession) -> dict[str, int]:
    """Seed or update India land and EEZ polygons into india_area."""
    # Path to pre-simplified seed JSON
    seed_json_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "data", "india_area_seed.json"
    )

    if not os.path.exists(seed_json_path):
        raise FileNotFoundError(f"Seed file not found at {seed_json_path}")

    with open(seed_json_path, "r", encoding="utf-8") as f:
        fc = json.load(f)

    inserted = 0
    updated = 0

    for feat in fc.get("features", []):
        props = feat.get("properties", {})
        name = props.get("name")
        area_type = props.get("area_type", "EEZ")
        source = props.get("source", "Unknown")
        area_km2 = props.get("area_km2")

        wkt_str = to_multipolygon_wkt(feat.get("geometry", {}))
        wkt_element = WKTElement(wkt_str, srid=4326)

        # Check existing record by unique name
        stmt = select(IndiaArea).where(IndiaArea.name == name)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.area_type = area_type
            existing.source = source
            existing.area_km2 = area_km2
            existing.geom = wkt_element
            updated += 1
            logger.info("Updated existing india_area record: '%s' (%s)", name, area_type)
        else:
            new_area = IndiaArea(
                id=uuid.uuid4(),
                name=name,
                area_type=area_type,
                source=source,
                area_km2=area_km2,
                geom=wkt_element,
            )
            session.add(new_area)
            inserted += 1
            logger.info("Inserted new india_area record: '%s' (%s)", name, area_type)

    await session.commit()
    logger.info("Seeding completed: %d inserted, %d updated", inserted, updated)
    return {"inserted": inserted, "updated": updated}


async def main() -> None:
    async with async_session_factory() as session:
        counts = await seed_india_area(session)
        print(f"Seed India Area result: {counts}")


if __name__ == "__main__":
    asyncio.run(main())
