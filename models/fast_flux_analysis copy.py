import enum
from sqlalchemy import Column, BigInteger, Enum, TIMESTAMP, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database import Base

class FastFluxType(enum.Enum):
    # Add all enum values from your DB if known
    SINGLE = "single"
    DOUBLE = "double"
    NAME = "name"
    UNKNOWN = "unknown"
    # ... add more as needed

class FastFluxAnalysis(Base):
    __tablename__ = "fast_flux_analysis"
    __table_args__ = (
        UniqueConstraint("domain_id", "flux_type", name="fast_flux_analysis_domain_id_flux_type_key"),
        Index("ff_analysis_domtypeff_idx", "domain_id", "flux_type"),
    )

    id = Column(BigInteger, primary_key=True)
    domain_id = Column(BigInteger, ForeignKey("domain.id", ondelete="CASCADE"))
    flux_type = Column(Enum(FastFluxType, name="fast_flux_type"), nullable=False)
    detected_on = Column(TIMESTAMP(timezone=True), nullable=False)

    domain = relationship("Domain", back_populates="fast_flux_analysis")
