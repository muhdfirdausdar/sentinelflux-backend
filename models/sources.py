from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Sources(Base):
    __tablename__ = "sources"

    # Define the columns for the source table
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    # Define the relationship with the Domain table
    domain = relationship("Domain", back_populates="sources", cascade="all, delete-orphan")

    # # Define the relationship with the domain_ip_malicious table
    domain_ip_malicious = relationship("DomainIPMalicious", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sources(id={self.id}, name={self.name})>"
