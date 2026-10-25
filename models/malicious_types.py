# models/malicious_types.py

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class MaliciousType(Base):
    __tablename__ = "malicious_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    domain_ip_malicious = relationship("DomainIPMalicious", back_populates="malicious_type", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MaliciousType(id={self.id}, name={self.name})>"
