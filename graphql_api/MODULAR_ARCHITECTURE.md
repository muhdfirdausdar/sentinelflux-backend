# GraphQL Modular Architecture

## Overview
Separated GraphQL implementation into independent, reusable modules based on database tables.

---

## ✅ New Structure

```
graphql_api/
├── queries/
│   ├── __init__.py
│   ├── domain.py       # Domain table queries
│   ├── source.py       # Sources table queries (NEW)
│   └── fast_flux.py    # FastFluxAnalysis table queries (NEW)
├── types/
│   ├── __init__.py
│   ├── domain.py       # Domain type + relationships
│   ├── source.py       # Source type (NEW)
│   └── fast_flux.py    # FastFluxAnalysis type (NEW)
├── mutations/
│   └── domain.py       # Domain mutations
├── filters/
│   ├── base.py
│   └── domain.py
├── enums.py
└── setup.py            # Combines all modules
```

---

## 🎯 Benefits

### 1. **Separation of Concerns**
Each database table has its own module:
- ✅ `source.py` - Only handles Sources table
- ✅ `fast_flux.py` - Only handles FastFluxAnalysis table  
- ✅ `domain.py` - Only handles Domain table

### 2. **Independent Queries**
Can query each table independently:

```graphql
# Query sources directly
{ 
  sources { 
    id 
    name 
  } 
}

# Query fast flux analysis directly
{ 
  fastFluxAnalysis(fluxType: SINGLE, limit: 10) { 
    id
    fluxType
    detectedOn
  } 
}

# Query domains
{ 
  domains { 
    items { 
      domainName 
    } 
  } 
}
```

### 3. **Cross-Module Relationships**
Domain can still access related data through relationships:

```graphql
{
  domains(limit: 5) {
    items {
      domainName
      
      # Relationship to Source module
      source {
        id
        name
      }
      
      # Relationship to FastFlux module
      fastFluxAnalysis(limit: 3) {
        id
        fluxType
        aRecordChangeFrequency
        nsRecordChangeFrequency
        detectedOn
      }
    }
  }
}
```

### 4. **Easier to Maintain**
- Want to modify Source queries? Edit `queries/source.py`
- Want to add FastFlux mutations? Edit `mutations/fast_flux.py`
- Clear file boundaries = less confusion

### 5. **Scalable**
Easy to add more tables:
1. Create `queries/ip_address.py`
2. Create `types/ip_address.py`
3. Add to `setup.py`: `class Query(DomainQuery, SourceQuery, FastFluxQuery, IPQuery)`
4. Done!

---

## 📋 Module Responsibilities

### **Source Module** (`source.py`)

#### Queries:
- `sources(limit, offset)` - Get all sources
- `source(id, name)` - Get specific source by ID or name
- `sources_count()` - Get total count

#### Type:
```python
@strawberry.type
class Source:
    id: int
    name: str
```

#### Example Query:
```graphql
{
  sources(limit: 10) {
    id
    name
  }
  
  source(name: "VirusTotal") {
    id
    name
  }
  
  sourcesCount
}
```

---

### **Fast Flux Module** (`fast_flux.py`)

#### Queries:
- `fast_flux_analysis(domain_id, flux_type, limit, offset)` - Get analysis with filters
- `fast_flux_analysis(id)` - Get specific analysis by ID

#### Type:
```python
@strawberry.type
class FastFluxAnalysis:
    id: int
    domain_id: int
    flux_type: FastFluxTypeEnum
    a_record_change_frequency: int
    ns_record_change_frequency: int
    detected_on: datetime
```

#### Example Query:
```graphql
{
  # Get all single flux analysis
  fastFluxAnalysis(fluxType: SINGLE, limit: 10) {
    id
    domainId
    fluxType
    aRecordChangeFrequency
    nsRecordChangeFrequency
    detectedOn
  }
  
  # Get analysis for specific domain
  fastFluxAnalysis(domainId: 5) {
    id
    fluxType
    detectedOn
  }
  
  # Get specific analysis
  fastFluxAnalysis(id: 100) {
    id
    fluxType
  }
}
```

---

### **Domain Module** (`domain.py`)

#### Queries:
- `domains(filter, sort, limit, offset)` - Get domains with advanced filtering

#### Type with Relationships:
```python
@strawberry.type
class Domain:
    # Domain fields
    id: int
    domain_name: str
    status: DomainStatusEnum
    # ... 9 more fields
    
    # Relationships (lazy-loaded)
    source() -> Optional[Source]                    # From source module
    fast_flux_analysis() -> List[FastFluxAnalysis]  # From fast_flux module
```

#### Example Query:
```graphql
{
  domains(
    filter: { status: ACTIVE }
    limit: 5
  ) {
    items {
      domainName
      status
      
      # Cross-module relationship
      source {
        name
      }
      
      # Cross-module relationship
      fastFluxAnalysis(limit: 2) {
        fluxType
        detectedOn
      }
    }
    totalCount
  }
}
```

---

## 🔄 How Modules Connect

### In `setup.py`:
```python
from .queries import DomainQuery, SourceQuery, FastFluxQuery

@strawberry.type
class Query(DomainQuery, SourceQuery, FastFluxQuery):
    """Combines all query modules"""
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

**Result**: All queries are available at the root level!

```graphql
{
  # From DomainQuery
  domains { ... }
  
  # From SourceQuery
  sources { ... }
  source(id: 1) { ... }
  
  # From FastFluxQuery
  fastFluxAnalysis { ... }
  fastFluxAnalysis(id: 1) { ... }
}
```

---

## 🔍 Cross-Module Relationships

### How Domain accesses Source:

In `types/domain.py`:
```python
from .source import Source  # Import from source module

@strawberry.type
class Domain:
    source_id: Optional[int]
    
    @strawberry.field
    async def source(self, info: Info) -> Optional[Source]:
        """Load source from Source module"""
        db = info.context["db"]
        query = select(SourcesModel).where(SourcesModel.id == self.source_id)
        result = await db.execute(query)
        source = result.scalar_one_or_none()
        return Source(id=source.id, name=source.name) if source else None
```

**Key Points:**
- ✅ Domain imports `Source` type from `source` module
- ✅ Relationship is lazy-loaded (only fetched when requested)
- ✅ Each module remains independent
- ✅ No circular dependencies

---

## 🆚 Before vs After

### **Before** (All in one file):
```python
# queries/domain.py (390 lines)
class DomainQuery:
    async def domains(...): ...
    async def domain(...): ...
    async def domain_by_name(...): ...
    async def domain_aggregations(...): ...
    # Also handles source and fast_flux filters

# types/common.py
class Source: ...
class FastFluxAnalysis: ...
```

**Problems:**
- ❌ Can't query sources independently
- ❌ Can't query fast_flux independently  
- ❌ Everything mixed together
- ❌ Hard to extend

---

### **After** (Modular):
```python
# queries/source.py
class SourceQuery:
    async def sources(...): ...
    async def source(...): ...

# queries/fast_flux.py
class FastFluxQuery:
    async def fast_flux_analysis(...): ...
    async def fast_flux_analysis(...): ...

# queries/domain.py
class DomainQuery:
    async def domains(...): ...  # Only domain logic
```

**Advantages:**
- ✅ Each module is independent
- ✅ Can query any table directly
- ✅ Easy to maintain
- ✅ Easy to extend
- ✅ Clear responsibilities

---

## 🚀 Usage Examples

### Get Sources
```graphql
{
  sources {
    id
    name
  }
}
```

### Get Fast Flux Analysis
```graphql
{
  fastFluxAnalysis(
    fluxType: DOUBLE
    limit: 10
  ) {
    id
    domainId
    fluxType
    detectedOn
  }
}
```

### Get Domains with Relationships
```graphql
{
  domains(limit: 5) {
    items {
      domainName
      source {        # From source module
        name
      }
      fastFluxAnalysis {  # From fast_flux module
        fluxType
      }
    }
  }
}
```

### Complex Cross-Module Query
```graphql
{
  # Get sources
  sources {
    id
    name
  }
  
  # Get fast flux analysis
  fastFluxAnalysis(fluxType: SINGLE, limit: 5) {
    id
    fluxType
  }
  
  # Get domains with relationships
  domains(
    filter: { status: ACTIVE }
    limit: 3
  ) {
    items {
      domainName
      source { name }
      fastFluxAnalysis { fluxType }
    }
  }
}
```

---

## 📝 Best Practices

### 1. **One Table = One Module**
Each database table gets its own query/type/mutation files

### 2. **Import Types, Not Queries**
```python
# ✅ Good
from .source import Source  # Import type

# ❌ Bad
from .source import SourceQuery  # Don't import queries
```

### 3. **Relationships in Type Files**
Keep relationship loaders in the type file, not query file

### 4. **Keep Filters Separate**
Create `filters/source.py` if Source needs complex filtering

---

## 🎯 Conclusion

**Is it a good idea?** 

### ✅ **YES! Absolutely!**

**Reasons:**
1. **Maintainable** - Each module is self-contained
2. **Scalable** - Easy to add new tables
3. **Reusable** - Query any table independently
4. **Clear** - No confusion about responsibilities
5. **Flexible** - Cross-module relationships still work perfectly

**When to use this pattern:**
- ✅ Multi-table applications (like yours)
- ✅ Team projects (clear ownership)
- ✅ Growing applications (easy to extend)
- ✅ Microservices-style architecture

**Your setup is now production-ready! 🚀**
