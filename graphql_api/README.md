# GraphQL API Module Structure

This directory contains the modular GraphQL implementation for SentinelFlux backend.

**Note:** This folder is named `graphql_api` (not `graphql`) to avoid naming conflicts with the `graphql-core` Python package.

## 📁 Directory Structure

```
graphql_api/
├── __init__.py                 # Package initialization
├── setup.py                    # Main schema setup and router configuration
├── enums.py                    # Shared enumerations (Status, Operators, etc.)
│
├── types/                      # GraphQL type definitions
│   ├── __init__.py
│   ├── common.py              # Shared types (Source, FastFluxAnalysis)
│   └── domain.py              # Domain-specific types
│
├── filters/                    # Filter input types
│   ├── __init__.py
│   ├── base.py                # Base filters (StringFilter, IntFilter, DateFilter)
│   └── domain.py              # Domain-specific filters
│
├── queries/                    # Query resolvers
│   ├── __init__.py
│   └── domain.py              # Domain query operations
│
└── mutations/                  # Mutation resolvers
    ├── __init__.py
    └── domain.py              # Domain mutation operations
```

## 🎯 Design Principles

### 1. **Separation of Concerns**
Each component has a specific responsibility:
- **Types**: Define data structures
- **Filters**: Define filtering logic
- **Queries**: Handle read operations
- **Mutations**: Handle write operations

### 2. **Modularity**
Each table/entity has its own files:
- `types/domain.py` - Domain types
- `queries/domain.py` - Domain queries
- `mutations/domain.py` - Domain mutations
- `filters/domain.py` - Domain filters

### 3. **Reusability**
Common components are shared:
- `enums.py` - Shared enums (operators, status)
- `types/common.py` - Shared types (Source, etc.)
- `filters/base.py` - Reusable filter types

### 4. **Extensibility**
Easy to add new entities:
```python
# Add new entity in 3 steps:

# 1. Create types/my_entity.py
# 2. Create queries/my_entity.py
# 3. Create mutations/my_entity.py

# 4. Update setup.py:
from .queries import DomainQuery, MyEntityQuery
from .mutations import DomainMutation, MyEntityMutation

@strawberry.type
class Query(DomainQuery, MyEntityQuery):
    pass

@strawberry.type
class Mutation(DomainMutation, MyEntityMutation):
    pass
```

## 🚀 Usage

### Import in main.py
```python
from graphql_api import create_graphql_router

# Create router
graphql_router = create_graphql_router()

# Include in FastAPI app
app.include_router(graphql_router, prefix="/graphql", tags=["GraphQL"])
```

### Access GraphiQL Playground
```
http://localhost:5252/graphql
```

## 📝 Adding New Entities

### Example: Adding IP Address GraphQL Support

#### 1. Create Type Definition
**File:** `graphql/types/ip.py`
```python
import strawberry
from typing import Optional

@strawberry.type
class IPAddress:
    id: int
    ip: str
    country: Optional[str]
    city: Optional[str]
    # ... other fields
```

#### 2. Create Filter Definition
**File:** `graphql/filters/ip.py`
```python
import strawberry
from typing import Optional
from .base import StringFilter, IntFilter

@strawberry.input
class IPFilterInput:
    ip: Optional[StringFilter] = None
    country: Optional[StringFilter] = None
    # ... other filters
```

#### 3. Create Query Resolver
**File:** `graphql/queries/ip.py`
```python
import strawberry
from strawberry.types import Info
from typing import List, Optional
from ..types.ip import IPAddress
from ..filters.ip import IPFilterInput

@strawberry.type
class IPQuery:
    @strawberry.field
    def ip_addresses(
        self, 
        info: Info,
        filter: Optional[IPFilterInput] = None,
        limit: int = 20
    ) -> List[IPAddress]:
        db = info.context["db"]
        # Query logic here
        return []
```

#### 4. Create Mutation Resolver
**File:** `graphql/mutations/ip.py`
```python
import strawberry
from strawberry.types import Info
from typing import Optional
from ..types.ip import IPAddress

@strawberry.type
class IPMutation:
    @strawberry.mutation
    def update_ip_location(
        self,
        info: Info,
        id: int,
        country: str
    ) -> Optional[IPAddress]:
        db = info.context["db"]
        # Update logic here
        return None
```

#### 5. Update Setup
**File:** `graphql/setup.py`
```python
from .queries import DomainQuery, IPQuery
from .mutations import DomainMutation, IPMutation

@strawberry.type
class Query(DomainQuery, IPQuery):
    pass

@strawberry.type
class Mutation(DomainMutation, IPMutation):
    pass
```

Done! Your new entity is now available in GraphQL.

## 🔧 Configuration

### Database Context
Database session is injected via context in `setup.py`:
```python
async def get_graphql_context(db: Session = Depends(get_db)) -> dict:
    return {"db": db}
```

Access in resolvers:
```python
@strawberry.field
def my_query(self, info: Info):
    db = info.context["db"]
    # Use db for queries
```

### Adding Authentication
Update context provider:
```python
from utils.auth import get_current_user

async def get_graphql_context(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return {
        "db": db,
        "user": current_user
    }
```

Access in resolvers:
```python
@strawberry.field
def protected_query(self, info: Info):
    user = info.context["user"]
    # Check permissions
```

## 📚 Key Files Explained

### `setup.py`
- Combines all queries and mutations
- Creates the GraphQL schema
- Configures context provider
- Exports router factory function

### `enums.py`
- Defines shared enumerations
- Operators (EQUALS, CONTAINS, etc.)
- Status types (ACTIVE, INACTIVE)
- Sort orders (ASC, DESC)

### `types/domain.py`
- Domain GraphQL type definition
- Matches SQLAlchemy Domain model
- Includes relationship resolvers (source, fastFluxAnalysis)

### `queries/domain.py`
- All read operations for domains
- Filter application logic
- Sorting and pagination
- Aggregations

### `mutations/domain.py`
- All write operations for domains
- Update status, remarks, etc.
- Returns updated domain data

### `filters/base.py`
- Reusable filter types
- StringFilter with operators
- IntFilter with numeric operators
- DateFilter with date operators

## 🎓 Best Practices

### 1. Keep Resolvers Thin
Move business logic to services:
```python
# ❌ Bad - logic in resolver
@strawberry.field
def domains(self, info: Info):
    db = info.context["db"]
    # 50 lines of complex logic...
    
# ✅ Good - use service layer
from services.domain_service import get_filtered_domains

@strawberry.field
def domains(self, info: Info, filter):
    db = info.context["db"]
    return get_filtered_domains(db, filter)
```

### 2. Use Type Hints
Always specify types for better IDE support:
```python
@strawberry.field
def domain(self, info: Info, id: int) -> Optional[Domain]:
    pass
```

### 3. Document Fields
Add descriptions to help users:
```python
@strawberry.field
def domains(self, info: Info, limit: int = 20) -> List[Domain]:
    """
    Get domains with pagination.
    
    Args:
        limit: Maximum number of results (default: 20)
    
    Returns:
        List of Domain objects
    """
    pass
```

### 4. Handle Errors Gracefully
```python
@strawberry.field
def domain(self, info: Info, id: int) -> Optional[Domain]:
    try:
        db = info.context["db"]
        domain = db.query(DomainModel).filter_by(id=id).first()
        return domain
    except Exception as e:
        logger.error(f"Error fetching domain {id}: {e}")
        return None
```

## 🔍 Testing

### Test in GraphiQL
1. Start server: `uvicorn main:app --reload`
2. Open: `http://localhost:5252/graphql`
3. Run queries interactively

### Unit Testing
```python
import pytest
from graphql import schema

@pytest.mark.asyncio
async def test_domain_query():
    query = """
        query {
            domain(id: 1) {
                id
                domainName
            }
        }
    """
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data["domain"]["id"] == 1
```

## 📖 Documentation

Full documentation available in `/docs/graphql/`:
- `GRAPHQL_USAGE_GUIDE.md` - Complete usage guide
- `GRAPHQL_QUICK_REFERENCE.md` - Quick reference
- `GRAPHQL_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `graphql_frontend_examples.tsx` - React examples

## 🚦 Next Steps

1. ✅ Implement GraphQL for other tables (IPs, nameservers)
2. ✅ Add authentication to GraphQL endpoints
3. ✅ Implement DataLoader for N+1 query optimization
4. ✅ Add subscriptions for real-time updates
5. ✅ Set up GraphQL testing framework
6. ✅ Add field-level authorization
7. ✅ Implement GraphQL caching strategy

## 🤝 Contributing

When adding new GraphQL features:
1. Follow the existing file structure
2. Add types in `types/`
3. Add filters in `filters/`
4. Add queries in `queries/`
5. Add mutations in `mutations/`
6. Update `setup.py` to include new classes
7. Document in appropriate MD files
