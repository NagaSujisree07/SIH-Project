from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.measurement import Measurement


class BGCMeasurement(Base):
    """
    Biogeochemical (BGC) Measurement Model.
    Represents ocean biogeochemical sensor parameters associated with physical depth measurements.
    """
    __tablename__ = "bgc_measurements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    measurement_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("measurements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="1-to-1 link to corresponding physical measurement record"
    )
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Direct foreign key for profile-level BGC query acceleration"
    )
    
    # Biogeochemical Parameters
    dissolved_oxygen_umol_kg: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Dissolved oxygen (umol/kg)")
    oxygen_saturation_pct: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Oxygen saturation percentage (%)")
    chlorophyll_mg_m3: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Chlorophyll-a concentration (mg/m^3)")
    nitrate_umol_kg: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Nitrate concentration (umol/kg)")
    ph: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Seawater pH")
    par_umol_m2_s: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Photosynthetically active radiation (umol/m^2/s)")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    measurement: Mapped["Measurement"] = relationship("Measurement", back_populates="bgc_measurement")
    profile: Mapped["Profile"] = relationship("Profile", back_populates="bgc_measurements")

    __table_args__ = (
        Index("idx_bgc_profile_id", "profile_id"),
    )

    def __repr__(self) -> str:
        return f"<BGCMeasurement(id={self.id}, measurement_id={self.measurement_id}, DO={self.dissolved_oxygen_umol_kg}, CHLA={self.chlorophyll_mg_m3})>"
