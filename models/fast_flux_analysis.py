from database import Base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ENUM, JSONB  # Use PostgreSQL ENUM and JSONB
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime


# CREATE TYPE fast_flux_type AS ENUM ('single', 'double', 'name', 'unknown');
# CREATE TABLE fast_flux_analysis (
#     id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
#     domain_id BIGINT REFERENCES domain(id) ON DELETE CASCADE,
#     flux_type fast_flux_type NOT NULL,
#     a_record_change_frequency INT NOT NULL,
#     ns_record_change_frequency INT NOT NULL,
#     detected_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#     details JSONB DEFAULT '{}'::JSONB,
#     UNIQUE (domain_id, flux_type)
# );

# Enum for fast flux types
class FastFluxType(str):
    SINGLE = "single"
    DOUBLE = "double"
    NAME = "name"
    UNKNOWN = "unknown"

class FastFluxAnalysis(Base):
    __tablename__ = "fast_flux_analysis"
    __table_args__ = (
        UniqueConstraint("domain_id", "flux_type", name="unique_domain_flux_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domain.id", ondelete="CASCADE"), nullable=False)
    flux_type: Mapped[str] = mapped_column(ENUM("single", "double", "name", "unknown", name="fast_flux_type", create_type=False), nullable=False)
    a_record_change_frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    ns_record_change_frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    domain = relationship("Domain", back_populates="fast_flux_analysis")

    def __repr__(self):
        return f"<FastFluxAnalysis(domain_id={self.domain_id}, flux_type='{self.flux_type}', a_freq={self.a_record_change_frequency}, ns_freq={self.ns_record_change_frequency})>"
