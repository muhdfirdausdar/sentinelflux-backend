from datetime import datetime
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from sqlalchemy.sql import func

class NameserverIP(Base):
    __tablename__ = "nameserver_ip"
    __table_args__ = (
        UniqueConstraint("nameserver_id", "ip_id", name="unique_nameserver_ip"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nameserver_id: Mapped[int] = mapped_column(ForeignKey("nameserver.id", ondelete="CASCADE"), nullable=False)
    ip_id: Mapped[int] = mapped_column(ForeignKey("ips.id", ondelete="CASCADE"), nullable=False)

    first_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    lowest_ttl_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    lowest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)

    highest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    highest_ttl_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


    # Relationships
    nameserver = relationship("Nameserver", back_populates="nameserver_ips")
    ip = relationship("IP", back_populates="nameserver_ips")

    def __repr__(self):
        return f"<NameserverIP(nameserver_id={self.nameserver_id}, ip_id={self.ip_id})>"
