from sqlalchemy import BigInteger, Text, String, ForeignKey, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import ENUM  # Use PostgreSQL ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional
from database import Base
from enum import Enum

# Enum for domain status
class DomainStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"




class Domain(Base):
    __tablename__ = "domain"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[str] = mapped_column(ENUM("active", "inactive", "unknown", name="domain_status", create_type=False), nullable=False)
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("sources.id", ondelete="SET NULL"))
    last_ff_analysis: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_analysis_done: Mapped[int] = mapped_column(BigInteger, default=0)
    domain_analysis_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wait_to_ff_analysis: Mapped[bool] = mapped_column(Boolean, default=True)
    is_unrated: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationship to the Source table
    fast_flux_analysis = relationship("FastFluxAnalysis", back_populates="domain", cascade="all, delete-orphan")
    sources = relationship("Sources", back_populates="domain", lazy="joined")
    domain_nameservers = relationship("DomainNameserver", back_populates="domain", cascade="all, delete-orphan")
    domain_ip_connections = relationship("DomainIPConnection", back_populates="domain")

    def __repr__(self):
        return f"<Domain(id={self.id}, domain_name={self.domain_name}, status={self.status})>"
