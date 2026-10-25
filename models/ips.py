# models/ips.py

from sqlalchemy import BigInteger, DateTime, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base

class IP(Base):
    __tablename__ = "ips"
    __table_args__ = (
        UniqueConstraint("ip_address", name="ips_ip_address_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    domain_ip_connections = relationship("DomainIPConnection", back_populates="ip", cascade="all, delete-orphan")
    ip_geolocations = relationship("IPGeolocation", back_populates="ip", cascade="all, delete-orphan")
    nameserver_ips = relationship("NameserverIP", back_populates="ip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<IP(id={self.id}, ip_address='{self.ip_address}')>"
