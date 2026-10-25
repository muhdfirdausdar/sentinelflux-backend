from sqlalchemy import BigInteger, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class HistoryNameserverIP(Base):
    __tablename__ = "history_ns_ip"

    ip_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    nameserver_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoryNameserverIP(ip_id={self.ip_id}, nameserver_id={self.nameserver_id}, ttl={self.ttl}, updated_at={self.updated_at})>"
