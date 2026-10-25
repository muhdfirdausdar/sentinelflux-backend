# SentinelFlux Backend

## Overview
SentinelFlux is a FastAPI backend for fast flux detection and analysis, featuring:
- Async logging and rate limiting
- Flexible credential management (local/prod) with Azure Key Vault support
- Modern FastAPI lifespan pattern
- Async PostgreSQL and Redis
- Inter-VM communication with robust connection pooling
- Failsafe HTTP client with auto-reconnect and health monitoring
- API key management and caching
- **Advanced Cursor-Based Pagination** with position tracking and bidirectional navigation

## Pagination System Guide

### 🎯 **Overview**
SentinelFlux implements sophisticated cursor-based pagination for efficient data navigation through large datasets. The system provides position tracking, bidirectional navigation capabilities, and comprehensive pagination metadata.

### 📊 **Current Response Format**
```json
{
  "status": "good",
  "remark": "Search successful", 
  "data": {
    "page_data": {
      "12694": {
        "domain_name": "example.com",
        "source_name": "ThreatFox",
        "is_malicious": true
      }
    },
    "data_count": 5,           // Items on current page
    "total_data": 29954,       // Total filtered results
    "at_data": 1,              // Current position (1-based)
    "next_cursor": "ZG9tYWluX2lkPTE..."  // Base64 encoded cursor
  }
}
```

### 🔧 **Navigation Strategies**

#### **1. First Page (No Cursor)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen
```
- `at_data`: 1
- `data_count`: 5  
- `total_data`: 29954
- Next cursor provided for page 2

#### **2. Next Page (Use Provided Cursor)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen&cursor=ZG9tYWluX2lkPTE...
```
- Use the `next_cursor` from previous response
- `at_data`: 6 (automatically calculated)
- New cursor provided for next page

#### **3. Previous Page (Frontend Cursor Manipulation)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen&cursor=MODIFIED_CURSOR
```
Frontend modifies the cursor by changing the position:
```javascript
// Example: Current page shows positions 6-10, go to previous (1-5)
const currentCursor = "ZG9tYWluX2lkPTE..."; // from API response
const decoded = JSON.parse(atob(currentCursor));
decoded.position = 1; // Calculate: current_position - limit = 6 - 5 = 1
const prevCursor = btoa(Object.entries(decoded).map(([k,v]) => `${k}=${v}`).join('&'));
```
- `at_data`: 1 (positions 1-5)
- Frontend calculates: `previous_position = current_at_data - limit`

#### **4. Last Page (Frontend Cursor Manipulation)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen&cursor=MODIFIED_CURSOR
```
Frontend calculates last page position:
```javascript
// Example: total_data = 29954, limit = 5, last page starts at position 29950
const lastPagePosition = Math.max(1, total_data - limit + 1); // 29954 - 5 + 1 = 29950
const decoded = JSON.parse(atob(currentCursor));
decoded.position = lastPagePosition;
const lastCursor = btoa(Object.entries(decoded).map(([k,v]) => `${k}=${v}`).join('&'));
```
- `at_data`: 29950 (positions 29950-29954)
- Frontend calculates: `last_position = total_data - limit + 1`

#### **5. Jump to Specific Page (Frontend Cursor Manipulation)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen&cursor=MODIFIED_CURSOR
```
Frontend calculates any page position:
```javascript
// Example: Jump to page 3 (positions 11-15)
const targetPage = 3;
const limit = 5;
const targetPosition = (targetPage - 1) * limit + 1; // (3-1) * 5 + 1 = 11
const decoded = JSON.parse(atob(currentCursor));
decoded.position = targetPosition;
const pageCursor = btoa(Object.entries(decoded).map(([k,v]) => `${k}=${v}`).join('&'));
```
- `at_data`: 11 (positions 11-15)
- Frontend calculates: `page_position = (page_number - 1) * limit + 1`

#### **3. Frontend Cursor Manipulation**
The frontend can manipulate cursor data directly for navigation:

**Decode → Modify → Encode**
```javascript
// Frontend JavaScript example
function navigateTo(currentCursor, targetPosition, limit) {
    // Decode current cursor
    const decodedCursor = JSON.parse(atob(currentCursor));
    
    // Modify position
    decodedCursor.position = targetPosition;
    
    // Encode back
    const queryString = Object.entries(decodedCursor)
        .map(([k, v]) => `${k}=${v}`)
        .join('&');
    const newCursor = btoa(queryString);
    
    // Make API call
    return fetch(`/search?limit=${limit}&cursor=${newCursor}`);
}

// Navigation examples
navigateTo(currentCursor, 1, 5);           // First page
navigateTo(currentCursor, 11, 5);          // Page 3 (positions 11-15)
navigateTo(currentCursor, totalData-4, 5); // Last page
```

### 📋 **Cursor Structure**

#### **Decoded Cursor Format**
```json
{
  "domain_id": 12345,
  "dom_last_seen": "2025-08-24T08:57:46.149674Z",
  "position": 6
}
```

#### **Encoding Process**
1. **Dictionary** → `{"domain_id": 12345, "position": 6}`
2. **Query String** → `domain_id=12345&position=6&dom_last_seen=2025-08-24...`
3. **Base64** → `ZG9tYWluX2lkPTEyMzQ1JnBvc2l0aW9uPTYmZG9tX2xhc3R...`

#### **2. Next Page (Using Cursor)**
```bash
GET /search?limit=5&fields=domain_name,source_name&sort=-dom_last_seen&cursor=ZG9tYWluX2lkPTE...
```
- `at_data`: 6 (with new cursor format)
- `data_count`: 5
- Continues pagination forward

#### **3. Frontend Display Logic**
```javascript
// Calculate display range
const startPos = response.data.at_data;
const endPos = startPos + response.data.data_count - 1; 
const total = response.data.total_data;

console.log(`Showing ${startPos} to ${endPos} from ${total} rows`);
// Output: "Showing 1 to 5 from 29954 rows"
```

### 🧭 **Cursor Structure**

#### **Raw Cursor Format (Before Encoding)**
```json
{
  "domain_id": 12345,
  "dom_last_seen": "2025-08-24T08:57:46.149674Z",
  "position": 6
}
```

#### **Query String Format (Intermediate)**
```
domain_id=12345&dom_last_seen=2025-08-24T08:57:46.149674Z&position=6
```

#### **Base64 Encoded (Final)**
```
ZG9tYWluX2lkPTEyMzQ1JmRvbV9sYXN0X3NlZW49MjAyNS0wOC0yNFQwODo1Nzo0Ni4xNDk2NzRaJnBvc2l0aW9uPTY=
```

### 💻 **Frontend Implementation Guide**

#### **React/JavaScript Pagination Component**
```jsx
function PaginationComponent({ response, onNavigate, limit = 10 }) {
    const { data_count, total_data, at_data, next_cursor } = response.data;
    
    // Calculate pagination metadata
    const currentPage = Math.ceil(at_data / limit);
    const totalPages = Math.ceil(total_data / limit);
    const endPosition = at_data + data_count - 1;
    const hasNextPage = endPosition < total_data;
    const hasPrevPage = at_data > 1;
    
    // Cursor manipulation utility
    const createCursorForPosition = (position) => {
        if (!next_cursor) return null;
        
        try {
            // Decode current cursor
            const decoded = JSON.parse(atob(next_cursor));
            
            // Modify position (ensure bounds)
            const safePosition = Math.max(1, Math.min(position, total_data));
            decoded.position = safePosition;
            
            // Re-encode
            const queryString = Object.entries(decoded)
                .map(([k, v]) => `${k}=${v}`)
                .join('&');
            return btoa(queryString);
        } catch (error) {
            console.error('Cursor manipulation failed:', error);
            return null;
        }
    };
    
    // Navigation handlers
    const goToFirst = () => onNavigate(createCursorForPosition(1));
    const goToPrev = () => onNavigate(createCursorForPosition(at_data - limit));
    const goToNext = () => onNavigate(next_cursor); // Use provided cursor
    const goToLast = () => onNavigate(createCursorForPosition(total_data - limit + 1));
    const goToPage = (page) => onNavigate(createCursorForPosition((page - 1) * limit + 1));
    
    return (
        <div className="pagination-container">
            {/* Display current range */}
            <div className="pagination-info">
                Showing {at_data.toLocaleString()} to {endPosition.toLocaleString()} of {total_data.toLocaleString()} results
            </div>
            
            {/* Navigation controls */}
            <div className="pagination-controls">
                <button onClick={goToFirst} disabled={!hasPrevPage}>
                    First
                </button>
                <button onClick={goToPrev} disabled={!hasPrevPage}>
                    Previous
                </button>
                
                <span className="page-info">
                    Page {currentPage} of {totalPages}
                </span>
                
                <button onClick={goToNext} disabled={!hasNextPage}>
                    Next
                </button>
                <button onClick={goToLast} disabled={!hasNextPage}>
                    Last
                </button>
            </div>
            
            {/* Page jump input */}
            <div className="page-jump">
                <input 
                    type="number" 
                    min="1" 
                    max={totalPages}
                    placeholder="Go to page..."
                    onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                            const page = parseInt(e.target.value);
                            if (page >= 1 && page <= totalPages) {
                                goToPage(page);
                                e.target.value = '';
                            }
                        }
                    }}
                />
            </div>
        </div>
    );
}
```

#### **Vue.js Implementation**
```vue
<template>
  <div class="pagination">
    <div class="pagination-info">
      Showing {{ startPos }} to {{ endPos }} of {{ totalData }} results
    </div>
    
    <div class="pagination-controls">
      <button @click="goToFirst" :disabled="!hasPrevPage">First</button>
      <button @click="goToPrev" :disabled="!hasPrevPage">Previous</button>
      <span>Page {{ currentPage }} of {{ totalPages }}</span>
      <button @click="goToNext" :disabled="!hasNextPage">Next</button>
      <button @click="goToLast" :disabled="!hasNextPage">Last</button>
    </div>
    
    <select @change="changePageSize" v-model="pageSize">
      <option value="5">5 per page</option>
      <option value="10">10 per page</option>
      <option value="25">25 per page</option>
      <option value="50">50 per page</option>
    </select>
  </div>
</template>

<script>
export default {
  props: ['paginationData'],
  data() {
    return {
      pageSize: 10
    };
  },
  computed: {
    totalData() { return this.paginationData.total_data; },
    startPos() { return this.paginationData.at_data; },
    endPos() { return this.startPos + this.paginationData.data_count - 1; },
    currentPage() { return Math.ceil(this.startPos / this.pageSize); },
    totalPages() { return Math.ceil(this.totalData / this.pageSize); },
    hasPrevPage() { return this.startPos > 1; },
    hasNextPage() { return this.endPos < this.totalData; }
  },
  methods: {
    manipulateCursor(targetPosition) {
      if (!this.paginationData.next_cursor) return null;
      
      const decoded = JSON.parse(atob(this.paginationData.next_cursor));
      decoded.position = Math.max(1, Math.min(targetPosition, this.totalData));
      
      const queryString = Object.entries(decoded)
        .map(([k, v]) => `${k}=${v}`)
        .join('&');
      return btoa(queryString);
    },
    
    goToFirst() {
      this.$emit('navigate', this.manipulateCursor(1));
    },
    
    goToPrev() {
      this.$emit('navigate', this.manipulateCursor(this.startPos - this.pageSize));
    },
    
    goToNext() {
      this.$emit('navigate', this.paginationData.next_cursor);
    },
    
    goToLast() {
      const lastPageStart = this.totalData - this.pageSize + 1;
      this.$emit('navigate', this.manipulateCursor(lastPageStart));
    },
    
    changePageSize() {
      // Recalculate position for new page size
      const currentItem = this.startPos;
      const newPageStart = Math.floor((currentItem - 1) / this.pageSize) * this.pageSize + 1;
      
      this.$emit('navigate', this.manipulateCursor(newPageStart), this.pageSize);
    }
  }
};
</script>
```

### ✅ **Advantages of Frontend Cursor Manipulation**

1. **🚀 Performance**: No backend complexity for multiple cursor types
2. **🎯 Flexibility**: Jump to any page directly without server round-trips  
3. **💾 Efficiency**: Single cursor format handles all navigation patterns
4. **🔧 Simplicity**: Reduced API surface area and implementation complexity
5. **⚡ Responsiveness**: Instant navigation calculations on the frontend

### ⚠️ **Best Practices & Considerations**

#### **Position Validation**
```javascript
function validatePosition(position, totalData, pageSize) {
    const minPosition = 1;
    const maxPosition = Math.max(1, totalData - pageSize + 1);
    return Math.max(minPosition, Math.min(position, maxPosition));
}

function safeCursorManipulation(cursor, newPosition, totalData, pageSize) {
    try {
        const decoded = JSON.parse(atob(cursor));
        decoded.position = validatePosition(newPosition, totalData, pageSize);
        
        const queryString = Object.entries(decoded)
            .map(([k, v]) => `${k}=${v}`)
            .join('&');
        return btoa(queryString);
    } catch (error) {
        console.error('Cursor manipulation error:', error);
        return null; // Trigger fallback to first page
    }
}
```

#### **Error Handling**
```javascript
async function navigateWithErrorHandling(cursor, fallbackToFirstPage = true) {
    try {
        const response = await fetch(`/search?cursor=${cursor}&limit=10`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Navigation failed:', error);
        
        if (fallbackToFirstPage) {
            // Fallback: load first page without cursor
            return await fetch('/search?limit=10').then(r => r.json());
        }
        
        throw error;
    }
}
```

#### **Performance Optimization**
```javascript
class PaginationCache {
    constructor(maxSize = 50) {
        this.cache = new Map();
        this.maxSize = maxSize;
    }
    
    // Cache cursor manipulations
    getCursor(basePosition, targetPosition) {
        const key = `${basePosition}->${targetPosition}`;
        return this.cache.get(key);
    }
    
    setCursor(basePosition, targetPosition, cursor) {
        const key = `${basePosition}->${targetPosition}`;
        
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, cursor);
    }
}
```

### 🔄 **Migration & Compatibility**

#### **Legacy Cursor Support**
- Cursors without `position` field default to `at_data = 1`
- Automatic upgrade to position tracking on next navigation
- No breaking changes for existing implementations

#### **Graceful Degradation**
```javascript
function handleLegacyCursor(cursor) {
    try {
        const decoded = JSON.parse(atob(cursor));
        
        if (!decoded.position) {
            // Legacy cursor - start fresh pagination
            console.warn('Legacy cursor detected, starting new pagination session');
            return null; // Will trigger first page load
        }
        
        return cursor;
    } catch (error) {
        console.error('Invalid cursor format:', error);
        return null;
    }
}
```

### 🎯 **Real-World Example: Complete Implementation**

```javascript
class PaginationManager {
    constructor(apiEndpoint, defaultPageSize = 10) {
        this.apiEndpoint = apiEndpoint;
        this.defaultPageSize = defaultPageSize;
        this.currentResponse = null;
    }
    
    // Load first page
    async loadFirstPage(filters = {}, pageSize = this.defaultPageSize) {
        const params = new URLSearchParams({
            limit: pageSize,
            ...filters
        });
        
        const response = await fetch(`${this.apiEndpoint}?${params}`);
        this.currentResponse = await response.json();
        return this.currentResponse;
    }
    
    // Navigate using cursor manipulation
    async navigateToPosition(position, pageSize = this.defaultPageSize) {
        if (!this.currentResponse?.data?.next_cursor) {
            return this.loadFirstPage({}, pageSize);
        }
        
        const cursor = this.createCursorForPosition(position);
        const params = new URLSearchParams({
            limit: pageSize,
            cursor: cursor
        });
        
        const response = await fetch(`${this.apiEndpoint}?${params}`);
        this.currentResponse = await response.json();
        return this.currentResponse;
    }
    
    // Utility methods
    createCursorForPosition(position) {
        const decoded = JSON.parse(atob(this.currentResponse.data.next_cursor));
        const safePosition = Math.max(1, Math.min(position, this.currentResponse.data.total_data));
        decoded.position = safePosition;
        
        const queryString = Object.entries(decoded)
            .map(([k, v]) => `${k}=${v}`)
            .join('&');
        return btoa(queryString);
    }
    
    // Navigation shortcuts
    async goToPage(page, pageSize = this.defaultPageSize) {
        const position = (page - 1) * pageSize + 1;
        return this.navigateToPosition(position, pageSize);
    }
    
    async goToFirst(pageSize = this.defaultPageSize) {
        return this.navigateToPosition(1, pageSize);
    }
    
    async goToLast(pageSize = this.defaultPageSize) {
        const lastPosition = this.currentResponse.data.total_data - pageSize + 1;
        return this.navigateToPosition(Math.max(1, lastPosition), pageSize);
    }
}

// Usage
const pagination = new PaginationManager('/search');

// Load first page
await pagination.loadFirstPage({ sort: '-dom_last_seen' });

// Navigate to page 5
await pagination.goToPage(5);

// Jump to last page
await pagination.goToLast();
```

### ⚙️ **Implementation Status**

#### **✅ Currently Implemented:**
- `total_data`: Total count of filtered results
- `at_data`: Current position tracking  
- `next_cursor`: Forward navigation
- Position tracking in new cursors
- Legacy cursor compatibility (defaults to position 1)

#### **🚧 Future Implementation Needed:**
- `prev_cursor`: Backward navigation
- `first_cursor`: Jump to first page
- `last_cursor`: Jump to last page  
- `current_page`: Page number calculation
- `total_pages`: Total page count
- Bidirectional cursor generation

### 🔄 **Advanced Navigation Requirements**

#### **1. Previous Page Implementation**
To implement backward navigation, the system needs:

```python
# In cursor generation, also create previous cursor
def generate_bidirectional_cursors(current_data, position, limit):
    next_cursor = {
        "domain_id": current_data[-1]["id"],
        "dom_last_seen": current_data[-1]["dom_last_seen"], 
        "position": position + limit,
        "direction": "forward"
    }
    
    prev_cursor = {
        "domain_id": current_data[0]["id"],
        "dom_last_seen": current_data[0]["dom_last_seen"],
        "position": max(1, position - limit),
        "direction": "backward"  
    }
    
    return next_cursor, prev_cursor
```

#### **2. Complete Response Format (Future)**
```json
{
  "data": {
    "page_data": {...},
    "data_count": 5,
    "total_data": 29954,
    "at_data": 6,
    "current_page": 2,
    "total_pages": 5991,
    "next_cursor": "ZG9tYWluX2lkPTE...",
    "prev_cursor": "cHJldl9kb21haW4...",
    "first_cursor": null,
    "last_cursor": "bGFzdF9kb21haW4..."
  }
}
```

#### **3. Navigation Logic**
```python
# Route modifications needed
@router.get("")
async def search_domain(
    limit: int = 10,
    cursor: Optional[str] = None,
    direction: str = "forward",  # New parameter
    # ... other params
):
    # Parse cursor and direction
    cursor_data = parse_cursor(cursor) if cursor else None
    nav_direction = cursor_data.get("direction", "forward") if cursor_data else "forward"
    
    # Modify query based on direction
    if nav_direction == "backward":
        # Reverse sort order and adjust logic
        is_desc = not is_desc
        # Implement backward pagination logic
```

### 📱 **Frontend Integration Example**

```javascript
class PaginationManager {
    constructor(apiBase) {
        this.apiBase = apiBase;
        this.currentParams = {};
    }
    
    async navigate(cursor = null, direction = "forward") {
        const params = new URLSearchParams({
            ...this.currentParams,
            ...(cursor && { cursor })
        });
        
        const response = await fetch(`${this.apiBase}/search?${params}`);
        const data = await response.json();
        
        this.updateUI(data.data);
        return data;
    }
    
    updateUI(data) {
        // Update pagination info
        const start = data.at_data;
        const end = start + data.data_count - 1;
        document.getElementById('pageInfo').textContent = 
            `Showing ${start} to ${end} from ${data.total_data} rows`;
            
        // Enable/disable buttons based on cursor availability
        document.getElementById('prevBtn').disabled = !data.prev_cursor;
        document.getElementById('nextBtn').disabled = !data.next_cursor;
        document.getElementById('firstBtn').disabled = !data.first_cursor;
        document.getElementById('lastBtn').disabled = !data.last_cursor;
    }
}
```

### 🔍 **Testing Pagination**

```bash
# Test basic pagination
curl "http://localhost:5252/search?limit=3&fields=domain_name,source_name"

# Test with cursor
curl "http://localhost:5252/search?limit=3&fields=domain_name,source_name&cursor=ZG9tYWluX2lk..."

# Test with sorting
curl "http://localhost:5252/search?limit=3&fields=domain_name,source_name&sort=-dom_last_seen"
```

### 💡 **Best Practices**

1. **Cursor Storage**: Store cursors temporarily on client side, not in database
2. **Position Tracking**: Always include position in new cursor format  
3. **Legacy Support**: Handle old cursors gracefully (default to position 1)
4. **Error Handling**: Validate cursor format and handle parsing errors
5. **Performance**: Use efficient database queries with proper indexing
6. **Security**: Validate cursor data to prevent injection attacks

### 🚀 **Performance Considerations**

- **Cursor-based pagination** is more efficient than offset-based for large datasets
- **Position tracking** enables accurate "showing X to Y of Z" displays
- **Database indexing** on sort columns is crucial for performance
- **Cursor validation** prevents malicious or corrupted cursor usage

## Key Features
- **Azure Key Vault Integration**: Secure credential management in production with environment fallbacks
- **Global HTTP Connection Pool**: Persistent, auto-reconnecting, health-monitored pool for VM2 communication
- **Pure Function Metadata API**: No class/init, just stateless async functions
- **API Key Buffering**: API keys fetched and cached in Redis for secure, fast access
- **Comprehensive Error Handling**: Retries, exponential backoff, and detailed logging
- **Single Source of Truth**: All documentation in this README

## Architecture
- `utils/azure_vault.py`: Centralized Azure Key Vault client with fallback support
- `utils/credential_manager.py`: Environment-aware credential management (local/prod)
- `dnflux_pool.py`: Global HTTP connection pool with failsafe features
- `dnflux_ops/metadata_handler.py`: Pure async functions for `/helper/metrics` and summary
- `utils/local_credentials.py`: Local development credential storage
- `routes/dnflux.py`: API endpoints for metadata, health, stats, and cache
- `models/`, `schemas/`, `services/`: Domain logic and DB models
- `routes/search_domain.py`: Advanced pagination endpoints with cursor navigation
- `services/pagination.py`: Core pagination logic with position tracking
- `schemas/pagination.py`: Pagination models and validation

## Azure Key Vault Configuration

### Required Secrets in Azure Key Vault:
- `sf-dbpass`: Database password for SentinelFlux 
- `sf-redispass`: Redis password for SentinelFlux
- `sf-apikey`: API key for SentinelFlux authentication
- `dnflux-apikey`: Internal API key for DNFlux VM2 communication

### Environment Variables:
- `AZURE_KEYVAULT_URL`: Your Azure Key Vault URL
- `DB_PASSWORD`: Fallback database password (if vault unavailable)
- `REDIS_PASSWORD`: Fallback Redis password (if vault unavailable)
- `API_KEY`: Fallback API key (if vault unavailable)
- `DNFLUX_INTERNAL_TOKEN`: Fallback DNFlux internal token (if vault unavailable)

### Local Development:
Set `AT_LOCAL_MACHINE=true` to use local credentials instead of Azure Key Vault.

## Usage
### Metadata

## Key Features
- **Azure Key Vault Integration**: Secure credential management in production with environment fallbacks
- **Global HTTP Connection Pool**: Persistent, auto-reconnecting, health-monitored pool for VM2 communication
- **Pure Function Metadata API**: No class/init, just stateless async functions
- **API Key Buffering**: API keys fetched and cached in Redis for secure, fast access
- **Comprehensive Error Handling**: Retries, exponential backoff, and detailed logging
- **Single Source of Truth**: All documentation in this README

## Architecture
- `utils/azure_vault.py`: Centralized Azure Key Vault client with fallback support
- `utils/credential_manager.py`: Environment-aware credential management (local/prod)
- `dnflux_pool.py`: Global HTTP connection pool with failsafe features
- `dnflux_ops/metadata_handler.py`: Pure async functions for `/helper/metrics` and summary
- `utils/local_credentials.py`: Local development credential storage
- `routes/dnflux.py`: API endpoints for metadata, health, stats, and cache
- `models/`, `schemas/`, `services/`: Domain logic and DB models

## Azure Key Vault Configuration

### Required Secrets in Azure Key Vault:
- `sf-dbpass`: Database password for SentinelFlux 
- `sf-redispass`: Redis password for SentinelFlux
- `sf-apikey`: API key for SentinelFlux authentication
- `dnflux-apikey`: Internal API key for DNFlux VM2 communication

### Environment Variables:
- `AZURE_KEYVAULT_URL`: Your Azure Key Vault URL
- `DB_PASSWORD`: Fallback database password (if vault unavailable)
- `REDIS_PASSWORD`: Fallback Redis password (if vault unavailable)
- `API_KEY`: Fallback API key (if vault unavailable)
- `DNFLUX_INTERNAL_TOKEN`: Fallback DNFlux internal token (if vault unavailable)

### Local Development:
Set `AT_LOCAL_MACHINE=true` to use local credentials instead of Azure Key Vault.

## Usage
### Metadata
```python
from dnflux_ops import get_metrics, get_metadata_summary
metrics = await get_metrics()
summary = await get_metadata_summary()
```

### Centralized Credential Management
```python
from utils.credential_manager import credential_manager

# Get credentials (automatically uses local or vault based on environment)
db_creds = await credential_manager.get_database_credentials()
redis_creds = await credential_manager.get_redis_credentials()
dnflux_creds = await credential_manager.get_dnflux_credentials()
api_key_creds = await credential_manager.get_sentinelflux_api_key()
```

### Azure Vault Credentials (Direct Access)
```python
from utils.azure_vault import vault_client
db_password = await vault_client.get_database_password()
redis_password = await vault_client.get_redis_password()
api_key = await vault_client.get_api_key()
dnflux_key = await vault_client.get_dnflux_apikey()
```

### Direct HTTP
```python
from dnflux_pool import dnflux_pool
client = dnflux_pool.get_client()
response = await client.get("/health")
```

### API Key Buffering
API keys are fetched and cached in Redis. Use the buffer key: `buffer:dnflux:apikey`.

## Failsafe Features
- Auto-reconnect on failure (3 attempts, exponential backoff)
- Health checks every 5 minutes
- Retry logic for all HTTP requests
- Connection stats available at `/dnflux/stats`
- Azure Key Vault with environment variable fallbacks

## Deployment
1. Configure `.env` for local/prod
2. Set up Azure Key Vault with required secrets
3. Configure `AZURE_KEYVAULT_URL` environment variable
2. Set up Azure Key Vault with required secrets
3. Configure `AZURE_KEYVAULT_URL` environment variable
4. Run with `uvicorn main:app --reload`
5. All documentation is in this README

## License
MIT
