# models/domain_nameserver.py

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, UniqueConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from sqlalchemy.sql import func
from datetime import datetime


class DomainNameserver(Base):
    __tablename__ = "domain_nameserver"
    __table_args__ = (
        UniqueConstraint("domain_id", "nameserver_id", name="unique_domain_nameserver"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domain.id", ondelete="SET NULL"), nullable=True)
    nameserver_id: Mapped[int] = mapped_column(ForeignKey("nameserver.id", ondelete="SET NULL"), nullable=True)

    first_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    lowest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    lowest_ttl_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    highest_ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    highest_ttl_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="domain_nameservers")
    nameserver = relationship("Nameserver", back_populates="domain_nameservers")

    def __repr__(self):
        return f"<DomainNameserver(domain_id={self.domain_id}, nameserver_id={self.nameserver_id})>"
