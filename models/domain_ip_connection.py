# models/domain_ip_connection.py

from sqlalchemy import BigInteger, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base
from .domain import Domain
from .ips import IP  # Assuming your IP table model is named `IP`

class DomainIPConnection(Base):
    __tablename__ = "domain_ip_connection"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("domain.id", ondelete="CASCADE"), nullable=False)
    ip_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ips.id", ondelete="CASCADE"), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    lowest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    lowest_ttl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    highest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    highest_ttl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="domain_ip_connections", lazy="joined")
    ip = relationship("IP", back_populates="domain_ip_connections", lazy="joined")
    malicious_entries = relationship("DomainIPMalicious", back_populates="domain_ip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DomainIPConnection(id={self.id}, domain_id={self.domain_id}, ip_id={self.ip_id})>"
