from sqlalchemy import BigInteger, Text, String, DateTime
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class HistoryDomain(Base):
    __tablename__ = "history_domain"

    domain_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(ENUM("active", "inactive", "unknown", name="domain_status", create_type=False), nullable=False)
    remarks: Mapped[str] = mapped_column(String(500), nullable=True)

    def __repr__(self):
        return f"<HistoryDomain(domain_id={self.domain_id}, status={self.status}, updated_at={self.updated_at})>"
