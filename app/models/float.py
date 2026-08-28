from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile


class Float(Base):
    """
    ARGO Float Platform Model.
    Represents an oceanographic profiling float platform.
    """
    __tablename__ = "floats"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True, doc="Unique platform ID (e.g. ARGO_001)")
    region: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, doc="Deployment oceanic region")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    profiles: Mapped[List["Profile"]] = relationship(
        "Profile",
        back_populates="float",
        cascade="all, delete-orphan",
        order_by="Profile.cycle_number"
    )

    def __repr__(self) -> str:
        return f"<Float(id='{self.id}', region='{self.region}')>"
