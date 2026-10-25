# Best Practices: Reusing Query Logic Across Modules

## Problem
You need to query multiple tables in one resolver. Should you:
1. Repeat the SQLAlchemy query logic?
2. Call the GraphQL resolver methods?
3. Create shared helper functions?

---

## ✅ Solution: Use All Three Patterns!

### **Pattern 1: Reuse GraphQL Resolvers (For Complete Objects)**

When you need the full GraphQL type with all fields:

```python
from .domain import DomainQuery
from .source import SourceQuery

@strawberry.type
class ComplexQuery:
    @strawberry.field
    async def get_domain_analysis(self, info: Info, domain_id: int):
        # ✅ Reuse existing resolvers
        domain_query = DomainQuery()
        source_query = SourceQuery()
        
        # Get domain using existing resolver
        domains = await domain_query.domains(
            info=info,
            filter=create_filter(id=domain_id),
            limit=1
        )
        
        domain = domains.items[0] if domains.items else None
        
        # Get source using existing resolver
        source = await source_query.source(
            info=info,
            id=domain.source_id
        ) if domain else None
        
        return {"domain": domain, "source": source}
```

**Use When:**
- ✅ You need the complete GraphQL type
- ✅ You want filtering/sorting/pagination logic
- ✅ Building complex nested queries

---

### **Pattern 2: Create Shared Helper Functions (For Raw Data)**

When you just need raw database data without GraphQL overhead:

```python
# graphql_api/utils/db_helpers.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.sources import Sources as SourcesModel
from models.domain import Domain as DomainModel

async def get_source_by_id(db: AsyncSession, source_id: int):
    """Reusable helper to get source - returns raw model"""
    query = select(SourcesModel).where(SourcesModel.id == source_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_domains_by_source(db: AsyncSession, source_id: int, limit: int = 10):
    """Reusable helper to get domains by source"""
    query = select(DomainModel).where(DomainModel.source_id == source_id).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

# Use in any resolver:
@strawberry.field
async def my_complex_query(self, info: Info):
    db = info.context["db"]
    
    # ✅ Reuse helper functions
    source = await get_source_by_id(db, 1)
    domains = await get_domains_by_source(db, 1, limit=5)
    
    return process_data(source, domains)
```

**Use When:**
- ✅ Need raw database objects
- ✅ Performing aggregations/calculations
- ✅ Query logic is simple (no filters/sorting needed)
- ✅ Performance critical (skip GraphQL type conversion)

---

### **Pattern 3: Use Native GraphQL Relationships (Best for Simple Cases)**

Let GraphQL handle it automatically:

```python
@strawberry.type
class Domain:
    source_id: Optional[int]
    
    @strawberry.field
    async def source(self, info: Info) -> Optional[Source]:
        """GraphQL automatically loads this when requested"""
        db = info.context["db"]
        # Query here - but client controls when it's called
        ...
        
# Client query decides what to load:
query {
  domains {
    items {
      domainName
      source { name }  # ← Only loads if client requests it
    }
  }
}
```

**Use When:**
- ✅ Simple parent-child relationships
- ✅ Want lazy loading (N+1 query optimization)
- ✅ Client decides what data to fetch

---

## 📊 Comparison Table

| Pattern | Use Case | Performance | Complexity |
|---------|----------|-------------|------------|
| **Reuse Resolvers** | Complete GraphQL objects with filters | Medium | Low |
| **Helper Functions** | Raw data, aggregations, calculations | High | Low |
| **GraphQL Relationships** | Simple parent-child, lazy loading | High* | Very Low |

*With proper dataloader implementation

---

## 🎯 Real Example: Complex Multi-Table Query

### Scenario: Get domain security report

```python
# queries/reports.py
from typing import Optional
import strawberry
from strawberry.types import Info

# Import helper functions
from ..utils.db_helpers import (
    get_source_by_id,
    get_domains_by_source,
    count_fast_flux_by_domain
)

# Import query classes for reuse
from .domain import DomainQuery
from .fast_flux import FastFluxQuery

@strawberry.type
class ReportQuery:
    """Complex reports combining multiple tables"""
    
    @strawberry.field
    async def security_report(
        self,
        info: Info,
        domain_id: int
    ) -> "SecurityReport":
        db = info.context["db"]
        
        # Pattern 1: Reuse GraphQL resolver for complete domain data
        domain_query = DomainQuery()
        domains = await domain_query.domains(
            info=info,
            filter=create_filter(id=domain_id),
            limit=1
        )
        
        if not domains.items:
            raise Exception("Domain not found")
        
        domain = domains.items[0]
        
        # Pattern 2: Use helper function for simple query
        source = await get_source_by_id(db, domain.source_id) if domain.source_id else None
        
        # Pattern 1: Reuse GraphQL resolver for analysis
        fast_flux_query = FastFluxQuery()
        analysis = await fast_flux_query.fast_flux_analysis(
            info=info,
            domain_id=domain_id,
            limit=100
        )
        
        # Pattern 2: Use helper for aggregation
        total_flux_count = await count_fast_flux_by_domain(db, domain_id)
        
        return SecurityReport(
            domain=domain,
            source_name=source.name if source else "Unknown",
            fast_flux_analysis=analysis,
            total_analysis=total_flux_count,
            risk_level=calculate_risk(domain, analysis)
        )


@strawberry.type
class SecurityReport:
    domain: Domain
    source_name: str
    fast_flux_analysis: List[FastFluxAnalysis]
    total_analysis: int
    risk_level: str
```

---

## 🛠️ Create the Helper Functions Module

```python
# graphql_api/utils/db_helpers.py
"""
Reusable database query helpers
Use these to avoid repeating SQLAlchemy queries across resolvers
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.sources import Sources as SourcesModel
from models.domain import Domain as DomainModel
from models.fast_flux_analysis import FastFluxAnalysis as FastFluxAnalysisModel


# ===== Source Helpers =====
async def get_source_by_id(db: AsyncSession, source_id: int) -> Optional[SourcesModel]:
    """Get source by ID - returns raw model"""
    query = select(SourcesModel).where(SourcesModel.id == source_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_source_by_name(db: AsyncSession, name: str) -> Optional[SourcesModel]:
    """Get source by name - returns raw model"""
    query = select(SourcesModel).where(SourcesModel.name == name)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# ===== Domain Helpers =====
async def get_domain_by_id(db: AsyncSession, domain_id: int) -> Optional[DomainModel]:
    """Get domain by ID - returns raw model"""
    query = select(DomainModel).where(DomainModel.id == domain_id)
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


async def count_domains_by_source(db: AsyncSession, source_id: int) -> int:
    """Count domains from specific source"""
    query = select(func.count(DomainModel.id)).where(
        DomainModel.source_id == source_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


# ===== Fast Flux Helpers =====
async def get_fast_flux_by_domain(
    db: AsyncSession,
    domain_id: int,
    flux_type: Optional[str] = None
) -> List[FastFluxAnalysisModel]:
    """Get fast flux analysis for domain"""
    query = select(FastFluxAnalysisModel).where(
        FastFluxAnalysisModel.domain_id == domain_id
    )
    
    if flux_type:
        query = query.where(FastFluxAnalysisModel.flux_type == flux_type)
    
    result = await db.execute(query)
    return result.scalars().all()


async def count_fast_flux_by_domain(db: AsyncSession, domain_id: int) -> int:
    """Count fast flux analysis for domain"""
    query = select(func.count(FastFluxAnalysisModel.id)).where(
        FastFluxAnalysisModel.domain_id == domain_id
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
```

---

## ✅ Benefits of This Approach

### 1. **DRY (Don't Repeat Yourself)**
```python
# Instead of repeating this everywhere:
query = select(SourcesModel).where(SourcesModel.id == source_id)
result = await db.execute(query)
source = result.scalar_one_or_none()

# Just call:
source = await get_source_by_id(db, source_id)
```

### 2. **Easy to Maintain**
Change query logic once, affects all callers:
```python
# Update helper function
async def get_source_by_id(db: AsyncSession, source_id: int):
    # Add caching, logging, error handling here
    # All callers automatically get the improvements!
    ...
```

### 3. **Type Safe**
Helper functions return SQLAlchemy models - type checker can verify

### 4. **Testable**
Easy to unit test helper functions independently

### 5. **Performance**
Skip GraphQL type conversion when you just need raw data

---

## 🎯 Decision Tree

```
Need data from another table?
│
├─ Need complete GraphQL type with relationships?
│  └─ ✅ Reuse GraphQL Resolver
│     Example: domain_query.domains(...)
│
├─ Just need simple raw data?
│  └─ ✅ Use Helper Function
│     Example: get_source_by_id(db, id)
│
├─ Client decides what to fetch?
│  └─ ✅ Use GraphQL Relationship
│     Example: @strawberry.field async def source(...)
│
└─ Complex aggregation across tables?
   └─ ✅ Use Helper Functions + Resolvers
      Example: helpers for data, resolvers for types
```

---

## 📝 Summary

**Your Question:** 
> "do we need to repeat again calling the sqlalchemy or can we just find the query resolver of each table"

**Answer:**
1. ✅ **Reuse GraphQL resolvers** when you need complete types with filters
2. ✅ **Create helper functions** for simple queries (best for raw data)
3. ✅ **Use GraphQL relationships** for lazy-loaded parent-child data
4. ❌ **Never repeat** the same SQLAlchemy query in multiple places

**Best Practice:**
- Put common queries in `graphql_api/utils/db_helpers.py`
- Call helper functions from any resolver
- Reuse GraphQL resolvers for complex filtering/sorting
- Keep code DRY (Don't Repeat Yourself)

This is how production GraphQL APIs are built! 🚀
