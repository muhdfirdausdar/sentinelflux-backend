# models/ip_geolocation.py

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base

class IPGeolocation(Base):
    __tablename__ = "ip_geolocation"
    __table_args__ = (
        UniqueConstraint("ip_id", "asn", "aso", name="unique_ip_geolocation"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_id: Mapped[int] = mapped_column(ForeignKey("ips.id", ondelete="CASCADE"), nullable=False)
    continent: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    latitude_longitude: Mapped[str] = mapped_column(String, nullable=False)
    asn: Mapped[int] = mapped_column(BigInteger, nullable=False)
    aso: Mapped[str] = mapped_column(String, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationship
    ip = relationship("IP", back_populates="ip_geolocations")

    def __repr__(self):
        return f"<IPGeolocation(ip_id={self.ip_id}, asn={self.asn}, country='{self.country}')>"
