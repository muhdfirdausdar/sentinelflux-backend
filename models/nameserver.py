# models/nameserver.py

from sqlalchemy import BigInteger, Column, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base



class Nameserver(Base):
    __tablename__ = "nameserver"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nameserver: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    domain_nameservers = relationship("DomainNameserver", back_populates="nameserver", cascade="all, delete-orphan")
    nameserver_ips = relationship("NameserverIP", back_populates="nameserver", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Nameserver(id={self.id}, nameserver='{self.nameserver}')>"
