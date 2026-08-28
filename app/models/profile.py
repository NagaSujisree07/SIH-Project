from datetime import date, datetime, timezone
from typing import List, TYPE_CHECKING
from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.float import Float
    from app.models.measurement import Measurement
    from app.models.bgc_measurement import BGCMeasurement


class Profile(Base):
    """
    ARGO Profile Model.
    Represents a single vertical water column cycle profile collected by a float at a specific location and date.
    """
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    float_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("floats.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cycle_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # PostGIS Point Geometry (SRID 4326 - WGS 84, Point(lon, lat))
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    float: Mapped["Float"] = relationship("Float", back_populates="profiles")
    measurements: Mapped[List["Measurement"]] = relationship(
        "Measurement",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Measurement.pressure_dbar"
    )
    bgc_measurements: Mapped[List["BGCMeasurement"]] = relationship(
        "BGCMeasurement",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("float_id", "cycle_number", name="uq_float_cycle"),
        Index("idx_profiles_date", "date"),
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, float_id='{self.float_id}', cycle={self.cycle_number}, date={self.date})>"
