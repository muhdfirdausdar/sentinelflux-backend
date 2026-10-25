"""
Database Query Helpers
Reusable functions to avoid repeating SQLAlchemy queries across resolvers
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.sources import Sources as SourcesModel
from models.domain import Domain as DomainModel
from models.fast_flux_analysis import FastFluxAnalysis as FastFluxAnalysisModel
from utils.input_sanitizer import InputSanitizer


# ===== Source Helpers =====

async def get_source_by_id(db: AsyncSession, source_id: int) -> Optional[SourcesModel]:
    """Get source by ID - returns raw SQLAlchemy model"""
    query = select(SourcesModel).where(SourcesModel.id == source_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_source_by_name(db: AsyncSession, name: str) -> Optional[SourcesModel]:
    """Get source by name - returns raw SQLAlchemy model"""
    query = select(SourcesModel).where(SourcesModel.name == name)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_sources(db: AsyncSession, limit: int = 100) -> List[SourcesModel]:
    """Get all sources"""
    query = select(SourcesModel).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ===== Domain Helpers =====

async def get_domain_by_id(db: AsyncSession, domain_id: int) -> Optional[DomainModel]:
    """Get domain by ID - returns raw SQLAlchemy model"""
    query = select(DomainModel).where(DomainModel.id == domain_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_domain_by_name(db: AsyncSession, domain_name: str) -> Optional[DomainModel]:
    """Get domain by name - returns raw SQLAlchemy model"""
    # Sanitize domain_name; if invalid, return None to indicate not found/invalid input
    try:
        domain_name = InputSanitizer.sanitize_domain_search(domain_name)
    except ValueError:
        return None

    query = select(DomainModel).where(DomainModel.domain_name == domain_name)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_domains_by_source(
    db: AsyncSession, 
    source_id: int, 
    limit: int = 10
) -> List[DomainModel]:
    """Get domains from specific source"""
    query = select(DomainModel).where(
        DomainModel.source_id == source_id
    ).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_domains_by_status(
    db: AsyncSession,
    status: str,
    limit: int = 10
) -> List[DomainModel]:
    """Get domains by status"""
    query = select(DomainModel).where(
        DomainModel.status == status
    ).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def count_domains_by_source(db: AsyncSession, source_id: int) -> int:
    """Count domains from specific source"""
    query = select(func.count(DomainModel.id)).where(
        DomainModel.source_id == source_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def count_domains_by_status(db: AsyncSession, status: str) -> int:
    """Count domains by status"""
    query = select(func.count(DomainModel.id)).where(
        DomainModel.status == status
    )
    result = await db.execute(query)
    return result.scalar() or 0


# ===== Fast Flux Helpers =====

async def get_fast_flux_by_id(
    db: AsyncSession,
    analysis_id: int
) -> Optional[FastFluxAnalysisModel]:
    """Get fast flux analysis by ID"""
    query = select(FastFluxAnalysisModel).where(
        FastFluxAnalysisModel.id == analysis_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_fast_flux_by_domain(
    db: AsyncSession,
    domain_id: int,
    flux_type: Optional[str] = None,
    limit: int = 10
) -> List[FastFluxAnalysisModel]:
    """Get fast flux analysis for domain"""
    query = select(FastFluxAnalysisModel).where(
        FastFluxAnalysisModel.domain_id == domain_id
    )
    
    if flux_type:
        query = query.where(FastFluxAnalysisModel.flux_type == flux_type)
    
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def count_fast_flux_by_domain(db: AsyncSession, domain_id: int) -> int:
    """Count fast flux analysis for domain"""
    query = select(func.count(FastFluxAnalysisModel.id)).where(
        FastFluxAnalysisModel.domain_id == domain_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def count_fast_flux_by_type(db: AsyncSession, flux_type: str) -> int:
    """Count fast flux analysis by type"""
    query = select(func.count(FastFluxAnalysisModel.id)).where(
        FastFluxAnalysisModel.flux_type == flux_type
    )
    result = await db.execute(query)
    return result.scalar() or 0


# ===== Cross-Table Helpers =====

async def get_domains_with_flux_type(
    db: AsyncSession,
    flux_type: str,
    limit: int = 10
) -> List[DomainModel]:
    """Get domains that have specific flux type"""
    query = select(DomainModel).join(
        FastFluxAnalysisModel
    ).where(
        FastFluxAnalysisModel.flux_type == flux_type
    ).distinct().limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_domains_with_source_and_flux(
    db: AsyncSession,
    source_id: int,
    flux_type: str,
    limit: int = 10
) -> List[DomainModel]:
    """Get domains from specific source that have specific flux type"""
    query = select(DomainModel).join(
        FastFluxAnalysisModel
    ).where(
        and_(
            DomainModel.source_id == source_id,
            FastFluxAnalysisModel.flux_type == flux_type
        )
    ).distinct().limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def count_domains_with_flux(db: AsyncSession) -> int:
    """Count total domains that have at least one fast flux analysis"""
    query = select(func.count(func.distinct(DomainModel.id))).select_from(
        DomainModel
    ).join(FastFluxAnalysisModel)
    
    result = await db.execute(query)
    return result.scalar() or 0
