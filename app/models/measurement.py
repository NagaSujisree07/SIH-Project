from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.bgc_measurement import BGCMeasurement


class Measurement(Base):
    """
    Core Physical Water Column Measurement Model.
    Represents physical sensor observations (pressure, depth, temperature, salinity, density)
    at a discrete vertical depth level of a profile.
    """
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    pressure_dbar: Mapped[float] = mapped_column(Float, nullable=False, doc="Pressure level (dbar)")
    depth_m: Mapped[float] = mapped_column(Float, nullable=False, index=True, doc="Approximate depth in meters")
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False, doc="In-situ temperature in Celsius")
    salinity: Mapped[float] = mapped_column(Float, nullable=False, doc="Practical salinity (PSU)")
    density_kg_m3: Mapped[float] = mapped_column(Float, nullable=False, doc="Seawater density (kg/m^3)")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="measurements")
    bgc_measurement: Mapped[Optional["BGCMeasurement"]] = relationship(
        "BGCMeasurement",
        back_populates="measurement",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "pressure_dbar", name="uq_profile_pressure"),
        Index("idx_measurements_depth_m", "depth_m"),
    )

    def __repr__(self) -> str:
        return f"<Measurement(id={self.id}, profile_id={self.profile_id}, pressure={self.pressure_dbar}, temp={self.temperature_c})>"
