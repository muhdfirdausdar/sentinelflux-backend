from sqlalchemy import BigInteger, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class HistoryGeoIP(Base):
    __tablename__ = "history_geoip"

    ip_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    continent: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    latitude_longitude: Mapped[str] = mapped_column(Text, nullable=False)  # Keep consistent with main schema
    asn: Mapped[int] = mapped_column(BigInteger, nullable=False)
    aso: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoryGeoIP(ip_id={self.ip_id}, country={self.country}, asn={self.asn}, updated_at={self.updated_at})>"
