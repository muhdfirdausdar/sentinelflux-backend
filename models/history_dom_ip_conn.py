from sqlalchemy import BigInteger, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class HistoryDomainIPConnection(Base):
    __tablename__ = "history_dom_ip_conn"

    domain_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    ip_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoryDomainIPConnection(domain_id={self.domain_id}, ip_id={self.ip_id}, ttl={self.ttl}, updated_at={self.updated_at})>"
