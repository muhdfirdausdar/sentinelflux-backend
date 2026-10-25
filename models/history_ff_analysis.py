from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class HistoryFastFluxAnalysis(Base):
    __tablename__ = "history_ff_analysis"

    domain_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    flux_type: Mapped[str] = mapped_column(ENUM("single", "double", "name", "unknown", name="fast_flux_type", create_type=False), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    a_record_change_frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    ns_record_change_frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoryFastFluxAnalysis(domain_id={self.domain_id}, flux_type={self.flux_type}, updated_at={self.updated_at})>"
