import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.report import WeatherReport


class EventCategory(Base):
    __tablename__ = "event_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    category_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    severity_default: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MODERATE",
    )
    color_hex: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    icon_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Relationships
    weather_reports: Mapped[List["WeatherReport"]] = relationship(
        "WeatherReport",
        back_populates="category",
    )
