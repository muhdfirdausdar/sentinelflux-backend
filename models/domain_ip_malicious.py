# models/domain_ip_malicious.py

from sqlalchemy import BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from database import Base
from .domain_ip_connection import DomainIPConnection
from .malicious_types import MaliciousType
from .sources import Sources

class DomainIPMalicious(Base):
    __tablename__ = "domain_ip_malicious"

    # Composite primary key - no id column
    domain_ip_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("domain_ip_connection.id", ondelete="CASCADE"), primary_key=True)
    malicious_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("malicious_types.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    domain_ip = relationship("DomainIPConnection", back_populates="malicious_entries", lazy="joined")
    malicious_type = relationship("MaliciousType", back_populates="domain_ip_malicious", lazy="joined")
    source = relationship("Sources", back_populates="domain_ip_malicious", lazy="joined")

    def __repr__(self):
        return f"<DomainIPMalicious(domain_ip_id={self.domain_ip_id}, malicious_type_id={self.malicious_type_id}, source_id={self.source_id})>"
