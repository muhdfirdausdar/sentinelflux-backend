# Domain Details Queries# Domain Details Multi-Query API# Domain Details Multi-Query API Documentation# Domain Details Summary Multi-Query



## Individual Queries



### 1. domDetailsSummaryMulti-query modules for the domain details page.

```graphql

{

  domDetailsSummary(domainId: 5) {

    id---This folder contains multi-query modules for the domain details page. Each module combines data from multiple tables to provide comprehensive information about a domain.## Overview

    domainName

    domainStatus

    sourceDomain

    isFastFlux## Available QueriesThis module provides a comprehensive summary of domain information by combining data from multiple GraphQL query modules.

    fluxType

    domFirstSeen

    domLastSeen

    isMalicious### 1. `domDetailsSummary(domainId: Int!)`## Overview

    sourceMalicious

    maliciousType**Returns:** Domain overview with counts and status

    lastMalUpdated

    totalARecords- Domain name, status, source, timestamps## File Structure

    totalNsRecords

    totalNsIps- Fast flux status and type

    aChangeFrequencyPerWeek

    nsChangeFrequencyPerWeek- Malicious status and typesThe domain details page makes multiple API calls to gather different aspects of domain information. This document outlines all available queries, their data sources, and identifies overlapping data that could be optimized.- `summary.py` - Main query implementation

  }

}- Total A records count

```

- Total NS records count- `../types/dom_details/summary.py` - Type definitions

### 2. aRecordInfo

```graphql- Total NS IPs count

{

  aRecordInfo(domainId: 5) {- Change frequencies (A/NS per week)---

    aRecords {

      id

      ipId

      ipAddress### 2. `aRecordInfo(domainId: Int!)`## Data Sources

      ttl

      lowestTtl**Returns:** Detailed A record information

      highestTtl

      firstSeen- **aRecords:** List of domain-IP connections## Available Queries

      lastSeen

      lowestTtlTime  - IP address, TTL (current/lowest/highest)

      country

      asnAso  - First seen, last seen, lowest TTL timeThe `dom_details_summary` query aggregates data from 6 different modules:

      latitudeLongitude

      maliciousTypes  - Geolocation (country, ASN/ASO, lat/long)

      maliciousSources

    }  - Malicious types and sources### 1. `domDetailsSummary` - Domain Overview Summary

    ipReuseInfo {

      ipId- **ipReuseInfo:** IP reuse statistics

      ipAddress

      totalRelationWithOtherDomains  - Total domains using each IP (excluding current)### 1. Domain Module (`DomainQuery`)

      totalRelationWithOtherNs

    }  - Total nameservers using each IP

  }

}**Purpose:** Provides a high-level summary of domain information including status, fast flux analysis, and record counts.- **Fields Retrieved:**

```

### 3. `aRecordAddon(ipId: Int!, domainId: Int!)`

### 3. aRecordAddon

```graphql**Returns:** Related entities for a specific IP (on-demand)  - `domain_name` - The domain name

{

  aRecordAddon(ipId: 10, domainId: 5) {- **relatedDomain:** Other domains using this IP

    relatedDomain {

      domainId  - Domain name, timestamps, flux type, malicious status**Data Sources:**  - `domain_status` - Current status (ACTIVE, SUSPENDED, etc.)

      domainName

      firstSeen- **relatedNameserver:** Nameservers using this IP

      lastSeen

      fluxType  - Nameserver name, timestamps, TTLs- Domain table (domain_name, status, first_seen, last_seen)  - `dom_first_seen` - First time domain was seen

      isMalicious

    }

    relatedNameserver {

      nameserverId### 4. `nsRecordInfo(domainId: Int!)`- Source table (source name)  - `dom_last_seen` - Last time domain was seen

      nameserverName

      firstSeen**Returns:** Detailed NS record information

      lastSeen

      lowestTtl- **nsRecords:** List of domain-nameserver connections- Fast Flux Analysis (is_fast_flux, flux_type, change frequencies)  - `source_id` - Reference to source

      latestTtl

    }  - Nameserver name, TTL, timestamps, countries

  }

}- **nsToIpsInfo:** Nameserver to IP mappings- Domain IP Connection (total A records count)

```

  - IP address, nameserver name

### 4. nsRecordInfo

```graphql  - TTLs, timestamps, geolocation (country, ASN/ASO)- Domain IP Malicious (malicious status, types, sources)### 2. Source Module (`SourceQuery`)

{

  nsRecordInfo(domainId: 5) {

    nsRecords {

      id### 5. `ipHoppingVisualization(domainId: Int!, daysBack: Int = 30)`- Domain Nameserver (total NS records count)- **Fields Retrieved:**

      nameserverId

      nameserver**Returns:** Historical IP changes grouped by time windows

      ttl

      lowestTtl- **timeGroups:** List of IP sets at different times- Nameserver IP (total NS IPs count)  - `source_domain` - Name of the source where domain was found

      highestTtl

      firstSeen  - Timestamp, list of IPs with lat/long

      lastSeen

      lowestTtlTime- Groups records within ±3 minutes (same DNS query)

      countries

    }- Skips duplicate groups (same IPs + locations)

    nsToIpsInfo {

      ipId- **Note:** Uses historical tables only**GraphQL Query:**### 3. Fast Flux Analysis Module (`FastFluxQuery`)

      ipAddress

      nsId

      nameserver

      ipNsTtl---```graphql- **Fields Retrieved:**

      ipNsLowestTtl

      firstSeen

      lastSeen

      ipNsLowestTtlTime## Data Overlaps{  - `is_fast_flux` - Boolean indicating if domain has fast flux records

      country

      asnAso

    }

  }### Can Be Combined/Optimized:  domDetailsSummary(domainId: 5) {  - `flux_type` - Type of fast flux (SINGLE, DOUBLE, NAME, NONE)

}

```



### 5. ipHoppingVisualization**domDetailsSummary ↔ aRecordInfo:**    id  - `A_change_frequency_per_week` - A record change frequency

```graphql

{- `totalARecords` from summary = `aRecords.length` from aRecordInfo

  ipHoppingVisualization(domainId: 5, daysBack: 30) {

    domainId- Client can derive count instead of separate query    domainName  - `NS_change_frequency_per_week` - NS record change frequency

    timeGroups {

      timestamp

      ips {

        ipAddress**domDetailsSummary ↔ nsRecordInfo:**    domainStatus

        latitude

        longitude- `totalNsRecords` from summary = `nsRecords.length` from nsRecordInfo

      }

    }- Client can derive count instead of separate query    sourceDomain### 4. Domain IP Connection Module (`DomainIPConnectionQuery`)

  }

}

```

**aRecordInfo ↔ nsRecordInfo:**    isFastFlux- **Functions Used:**

---

- Both fetch IP geolocation (country, ASN/ASO)

## Combined Query Structure

- Same IPs may appear in both (NS can be on same IP as A records)    fluxType  - `domain_ip_connection_info_by_id()` - Get total A records count

```graphql

{- Consider caching geolocation by IP ID

  # Summary + Details Combined

  domDetailsSummary(domainId: 5) {    domFirstSeen  - `get_domain_ip_ids_by_domain()` - Get list of domain_ip_connection IDs

    id

    domainName**domDetailsSummary ↔ aRecordInfo ↔ aRecordAddon:**

    domainStatus

    sourceDomain- All query malicious information    domLastSeen- **Fields Retrieved:**

    isFastFlux

    fluxType- Summary: aggregate malicious status

    domFirstSeen

    domLastSeen- aRecordInfo: malicious per IP    isMalicious  - `total_A_records` - Total number of A records (IPs) for the domain

    isMalicious

    sourceMalicious- aRecordAddon: malicious for related domains

    maliciousType

    lastMalUpdated    sourceMalicious  - `domain_ip_ids` - List of connection IDs (used for malicious check)

    # totalARecords          # <-- Can derive from aRecordInfo.aRecords.length

    # totalNsRecords         # <-- Can derive from nsRecordInfo.nsRecords.length### Mutually Exclusive:

    totalNsIps

    aChangeFrequencyPerWeek    maliciousType

    nsChangeFrequencyPerWeek

  }**ipHoppingVisualization:**

  

  aRecordInfo(domainId: 5) {- Uses historical tables only (history_domain_ip_conn, history_geoip)    lastMalUpdated### 5. Domain IP Malicious Module (`DomainIPMaliciousQuery`)

    aRecords {

      id- No overlap with current state queries

      ipId

      ipAddress- Separate feature for visualization tab    totalARecords- **Functions Used:**

      ttl

      lowestTtl

      highestTtl

      firstSeen**aRecordAddon:**    totalNsRecords  - `domain_ip_malicious_stats()` - Get aggregated malicious statistics

      lastSeen

      lowestTtlTime- On-demand query (triggered by user clicking IP)

      country                # <-- Overlaps with nsRecordInfo.nsToIpsInfo.country

      asnAso                 # <-- Overlaps with nsRecordInfo.nsToIpsInfo.asnAso- Different access pattern from page load queries    totalNsIps  - `domain_ip_malicious()` - Get individual malicious records

      latitudeLongitude

      maliciousTypes

      maliciousSources

    }---    aChangeFrequencyPerWeek- **Fields Retrieved:**

    ipReuseInfo {

      ipId

      ipAddress

      totalRelationWithOtherDomains## Typical Usage    nsChangeFrequencyPerWeek  - `is_malicious` - Boolean indicating if domain has malicious records

      totalRelationWithOtherNs

    }

  }

  ```graphql  }  - `malicious_type` - Dictionary of malicious type names

  nsRecordInfo(domainId: 5) {

    nsRecords {# 1. Page Load - Get overview and details

      id

      nameserverId{}  - `source_malicious` - Source name of latest malicious record

      nameserver

      ttl  domDetailsSummary(domainId: 5) { ... }

      lowestTtl

      highestTtl  aRecordInfo(domainId: 5) { ... }```  - `last_mal_updated` - Last seen timestamp of malicious activity

      firstSeen

      lastSeen  nsRecordInfo(domainId: 5) { ... }

      lowestTtlTime

      countries}

    }

    nsToIpsInfo {

      ipId

      ipAddress# 2. Optional - Visualization tab**Returns:**### 6. Domain Nameserver Module (`DomainNameserverQuery`)

      nsId

      nameserver{

      ipNsTtl

      ipNsLowestTtl  ipHoppingVisualization(domainId: 5, daysBack: 30) { ... }- Basic domain info- **Functions Used:**

      firstSeen

      lastSeen}

      ipNsLowestTtlTime

      country                # <-- Overlaps with aRecordInfo.aRecords.country- Fast flux classification  - `count_domain_nameservers()` - Get count and list of nameserver IDs

      asnAso                 # <-- Overlaps with aRecordInfo.aRecords.asnAso

    }# 3. On-demand - User clicks IP

  }

  {- Malicious status- **Fields Retrieved:**

  # Separate - Optional visualization

  # ipHoppingVisualization(domainId: 5, daysBack: 30) {  aRecordAddon(ipId: 10, domainId: 5) { ... }

  #   domainId

  #   timeGroups {}- Record counts (A and NS)  - `total_NS_records` - Total number of nameserver records

  #     timestamp

  #     ips {```

  #       ipAddress

  #       latitude- Change frequencies  - `nameserver_ids` - List of nameserver IDs (used for NS IP count)

  #       longitude

  #     }---

  #   }

  # }

  

  # On-demand - When user clicks IP## Optimization Tips

  # aRecordAddon(ipId: 10, domainId: 5) {

  #   relatedDomain {---### 7. Nameserver IP Module (`NameserverIPQuery`)

  #     domainId

  #     domainName1. **Client-side:** Extract counts from detailed queries instead of calling summary

  #     firstSeen

  #     lastSeen2. **Server-side:** Cache IP geolocation (rarely changes)- **Functions Used:**

  #     fluxType

  #     isMalicious3. **Architecture:** Consider DataLoader for batching similar queries

  #   }

  #   relatedNameserver {### 2. `aRecordInfo` - A Record Details  - `count_ips_for_nameservers()` - Count total IPs for given nameservers

  #     nameserverId

  #     nameserverName- **Fields Retrieved:**

  #     firstSeen

  #     lastSeen**Purpose:** Provides detailed information about all A records (IP addresses) for a domain, including geolocation and reuse statistics.  - `total_NS_IPs` - Total number of IPs across all nameservers

  #     lowestTtl

  #     latestTtl

  #   }

  # }**Data Sources:**## GraphQL Query Example

}

```- Domain IP Connection (all IP connections for domain)



### Overlaps:- IPs table (IP address strings)```graphql

- `totalARecords` = `aRecordInfo.aRecords.length`

- `totalNsRecords` = `nsRecordInfo.nsRecords.length`- IP Geolocation (country, ASN, ASO, latitude/longitude){

- `country`, `asnAso` in both `aRecordInfo` and `nsRecordInfo` (same IPs may appear)

- `maliciousTypes` overlap: summary aggregate vs per-IP detail- Domain IP Malicious (malicious types and sources per IP)  domDetailsSummary(domainId: 5) {


- Domain IP Connection (count of other domains using same IPs)    id

- Nameserver IP (count of nameservers using same IPs)    domainName

    domainStatus

**GraphQL Query:**    sourceDomain

```graphql    isFastFlux

{    fluxType

  aRecordInfo(domainId: 5) {    domFirstSeen

    aRecords {    domLastSeen

      id    isMalicious

      ipId    sourceMalicious

      ipAddress    maliciousType

      ttl    lastMalUpdated

      lowestTtl    totalARecords

      highestTtl    totalNsRecords

      firstSeen    totalNsIPs

      lastSeen    aChangeFrequencyPerWeek

      lowestTtlTime    nsChangeFrequencyPerWeek

      country  }

      asnAso}

      latitudeLongitude```

      maliciousTypes

      maliciousSources## Example Response

    }

    ipReuseInfo {```json

      ipId{

      ipAddress  "domDetailsSummary": {

      totalRelationWithOtherDomains    "id": 5,

      totalRelationWithOtherNs    "domainName": "example.com",

    }    "domainStatus": "ACTIVE",

  }    "sourceDomain": "VirusTotal",

}    "isFastFlux": true,

```    "fluxType": "SINGLE",

    "domFirstSeen": "2025-01-15T10:30:00+00:00",

**Returns:**    "domLastSeen": "2025-11-13T14:20:00+00:00",

- Complete list of A records with details    "isMalicious": true,

- Geolocation for each IP    "sourceMalicious": "AbuseIPDB",

- Malicious information per IP    "maliciousType": {

- IP reuse statistics      "type_1": "Phishing",

      "type_2": "Malware"

---    },

    "lastMalUpdated": "2025-11-10T08:15:00+00:00",

### 3. `aRecordAddon` - Related Domains and Nameservers for IP    "totalARecords": 15,

    "totalNsRecords": 4,

**Purpose:** For a specific IP, shows what other domains and nameservers are using it. Used as an addon query when user clicks on an IP.    "totalNsIPs": 8,

    "aChangeFrequencyPerWeek": 5,

**Data Sources:**    "nsChangeFrequencyPerWeek": 2

- Domain IP Connection (list of domains using this IP)  }

- Domain table (domain names and timestamps)}

- Fast Flux Analysis (flux type for each domain)```

- Domain IP Malicious (malicious status for each domain)

- Nameserver IP (list of nameservers using this IP)## Implementation Details

- Nameserver table (nameserver names)

- Nameserver IP connection details (TTLs, timestamps)### Multi-Query Pattern

This module follows the same pattern as `dom_flux_lookup.py`:

**GraphQL Query:**- No direct SQLAlchemy queries

```graphql- Reuses existing query modules

{- Combines data from multiple sources

  aRecordAddon(ipId: 10, domainId: 5) {- Returns a comprehensive result

    relatedDomain {

      domainId### Error Handling

      domainName- Returns `None` if domain doesn't exist

      firstSeen- Provides default values for missing data:

      lastSeen  - `is_fast_flux = False` if no fast flux records

      fluxType  - `is_malicious = False` if no malicious records

      isMalicious  - `total_NS_IPs = 0` if no nameservers

    }  - Empty strings for missing source/malicious data

    relatedNameserver {

      nameserverId### Performance Considerations

      nameserverName- Uses efficient query functions from existing modules

      firstSeen- Minimizes database calls by using aggregate functions

      lastSeen- Fetches only necessary data for each field

      lowestTtl

      latestTtl## Dependencies

    }

  }This module depends on the following query modules:

}- `graphql_api.queries.domain`

```- `graphql_api.queries.fast_flux`

- `graphql_api.queries.domain_ip_connection`

**Returns:**- `graphql_api.queries.domain_ip_malicious`

- List of domains using this IP- `graphql_api.queries.domain_nameserver`

- List of nameservers using this IP- `graphql_api.queries.nameserver_ip`

- Details for each relationship- `graphql_api.queries.source`



---All dependencies must be properly registered in the GraphQL schema.


### 4. `nsRecordInfo` - NS Record Details

**Purpose:** Provides detailed information about all NS records (nameservers) for a domain and their IP addresses.

**Data Sources:**
- Domain Nameserver (all NS connections for domain)
- Nameserver table (nameserver names)
- Nameserver IP (IP connections for each nameserver)
- IPs table (IP address strings)
- IP Geolocation (country, ASN, ASO)

**GraphQL Query:**
```graphql
{
  nsRecordInfo(domainId: 5) {
    nsRecords {
      id
      nameserverId
      nameserver
      ttl
      lowestTtl
      highestTtl
      firstSeen
      lastSeen
      lowestTtlTime
      countries
    }
    nsToIpsInfo {
      ipId
      ipAddress
      nsId
      nameserver
      ipNsTtl
      ipNsLowestTtl
      firstSeen
      lastSeen
      ipNsLowestTtlTime
      country
      asnAso
    }
  }
}
```

**Returns:**
- Complete list of NS records
- All IPs for each nameserver
- Geolocation for each IP
- Connection details (TTLs, timestamps)

---

### 5. `ipHoppingVisualization` - IP Change History Visualization

**Purpose:** Visualizes how domain IPs have changed over time by grouping historical records into time windows. Used for detecting IP hopping patterns.

**Data Sources:**
- History Domain IP Connection (historical IP records)
- IPs table (IP address strings)
- History GeoIP (geolocation at specific times)

**GraphQL Query:**
```graphql
{
  ipHoppingVisualization(domainId: 5, daysBack: 30) {
    domainId
    timeGroups {
      timestamp
      ips {
        ipAddress
        latitude
        longitude
      }
    }
  }
}
```

**Returns:**
- Time-grouped IP changes
- Geolocation at each time point
- Only unique groups (duplicates removed)

**Note:** This query is **mutually exclusive** - it uses historical tables and doesn't overlap with current state queries.

---

## Data Overlap Analysis

### High Overlap Areas

#### 1. **Domain Basic Info**
- **Used by:** `domDetailsSummary`
- **Data:** domain_name, status, first_seen, last_seen, source
- **Optimization:** Cache this data or fetch once and reuse

#### 2. **Domain IP Connection Count**
- **Used by:** `domDetailsSummary`, `aRecordInfo`
- **Overlap:** Both query total count of A records
- **domDetailsSummary:** Gets count only
- **aRecordInfo:** Gets full details of all records
- **Optimization:** Client can extract count from `aRecordInfo` instead of calling summary

#### 3. **Nameserver Count**
- **Used by:** `domDetailsSummary`, `nsRecordInfo`
- **Overlap:** Both query nameserver IDs and counts
- **domDetailsSummary:** Gets count only
- **nsRecordInfo:** Gets full details of all NS records
- **Optimization:** Client can count NS records from `nsRecordInfo`

#### 4. **Fast Flux Analysis**
- **Used by:** `domDetailsSummary`, `aRecordAddon` (for related domains)
- **Overlap:** Flux type and status
- **Optimization:** Cache flux status for the main domain

#### 5. **IP Geolocation**
- **Used by:** `aRecordInfo`, `nsRecordInfo`
- **Overlap:** Same IPs may appear in both A records and NS IPs
- **Optimization:** Cache geolocation by IP ID

### Medium Overlap Areas

#### 6. **Domain IP Malicious Info**
- **Used by:** `domDetailsSummary`, `aRecordInfo`, `aRecordAddon`
- **Overlap:** Malicious status and types
- **domDetailsSummary:** Summary of malicious status
- **aRecordInfo:** Detailed malicious info per IP
- **aRecordAddon:** Malicious status for related domains
- **Optimization:** Cache malicious data by domain_ip_id

#### 7. **Nameserver IP Connections**
- **Used by:** `domDetailsSummary` (count), `nsRecordInfo` (details), `aRecordInfo` (count per IP)
- **Overlap:** Multiple queries fetch nameserver-IP relationships
- **Optimization:** Cache NS-IP relationships

### No Overlap Areas

#### 8. **IP Hopping Visualization**
- **Used by:** `ipHoppingVisualization` only
- **Source:** Historical tables (separate from current state)
- **Overlap:** None - completely separate data set
- **Note:** Mutually exclusive with other queries

#### 9. **A Record Addon (Related Entities)**
- **Used by:** `aRecordAddon` only
- **Purpose:** On-demand query when user interacts with specific IP
- **Overlap:** Minimal - uses same underlying tables but different query pattern

---

## Optimization Recommendations

### 1. **Client-Side Optimizations**

**Reduce API Calls:**
- Extract `totalARecords` from `aRecordInfo.aRecords.length` instead of calling `domDetailsSummary`
- Extract `totalNsRecords` from `nsRecordInfo.nsRecords.length` instead of calling `domDetailsSummary`
- Cache domain basic info (name, status, timestamps) across components

**Query Order:**
```
1. domDetailsSummary (small, fast - get overview first)
2. aRecordInfo (medium - detailed A records)
3. nsRecordInfo (medium - detailed NS records)
4. ipHoppingVisualization (optional - only if needed)
5. aRecordAddon (on-demand - only when user clicks IP)
```

### 2. **Server-Side Optimizations**

**Consider DataLoader Pattern:**
- Batch IP geolocation lookups
- Batch nameserver lookups
- Cache frequently accessed data (domain info, flux status)

**Database Query Optimization:**
- Use `JOIN` instead of multiple queries where possible
- Consider materialized views for aggregated data
- Add indexes on frequently queried columns

### 3. **Caching Strategy**

**Cache Duration Recommendations:**
- Domain basic info: 5 minutes
- Flux status: 10 minutes
- IP geolocation: 1 hour (rarely changes)
- Malicious status: 5 minutes (security-sensitive)
- NS-IP relationships: 15 minutes

---

## Usage Pattern

### Typical Page Load Sequence:

1. **Initial Load:**
   ```graphql
   # Get overview first
   domDetailsSummary(domainId: 5)
   
   # Then get detailed records
   aRecordInfo(domainId: 5)
   nsRecordInfo(domainId: 5)
   ```

2. **Optional - Visualization Tab:**
   ```graphql
   # Only load if user opens visualization tab
   ipHoppingVisualization(domainId: 5, daysBack: 30)
   ```

3. **On-Demand - User Interaction:**
   ```graphql
   # Only when user clicks on specific IP
   aRecordAddon(ipId: 10, domainId: 5)
   ```

---

## Field Mapping Reference

### Common Fields Across Queries

| Field | domDetailsSummary | aRecordInfo | nsRecordInfo | ipHoppingVis |
|-------|------------------|-------------|--------------|--------------|
| domain_id | ✓ | ✓ | ✓ | ✓ |
| domain_name | ✓ | - | - | - |
| ip_address | - | ✓ | ✓ | ✓ |
| country | - | ✓ | ✓ | - |
| asn_aso | - | ✓ | ✓ | - |
| latitude/longitude | - | ✓ | - | ✓ |
| malicious_types | ✓ | ✓ | - | - |
| ttl | - | ✓ | ✓ | - |
| first_seen | ✓ | ✓ | ✓ | - |
| last_seen | ✓ | ✓ | ✓ | - |

---

## Performance Considerations

### Query Complexity (Estimated Response Time)

1. **domDetailsSummary:** Fast (~100-300ms)
   - Aggregates from multiple tables
   - Returns summary data only

2. **aRecordInfo:** Medium (~200-800ms)
   - Fetches all A records with details
   - Multiple sub-queries for geolocation and malicious data

3. **nsRecordInfo:** Medium (~200-800ms)
   - Fetches all NS records with IP details
   - Multiple sub-queries for each nameserver

4. **ipHoppingVisualization:** Slow (~500-2000ms)
   - Queries historical tables
   - Groups and processes large datasets
   - Calculates hashes for duplicate detection

5. **aRecordAddon:** Fast-Medium (~100-500ms)
   - On-demand query
   - Limited scope (single IP)

### Recommendations for Frontend:
- Show `domDetailsSummary` immediately
- Load `aRecordInfo` and `nsRecordInfo` with loading indicators
- Lazy-load `ipHoppingVisualization` (separate tab/component)
- Load `aRecordAddon` on user interaction (modal/drawer)

---

## Future Enhancements

1. **Unified Query:** Consider creating a single comprehensive query that returns all data at once (for clients that need everything)

2. **GraphQL DataLoader:** Implement batching and caching at the resolver level

3. **Subscription Support:** Add real-time updates for malicious status changes

4. **Pagination:** Add pagination support for large result sets (especially in `aRecordInfo` and `nsRecordInfo`)

5. **Field-Level Caching:** Cache individual fields (like geolocation) at the GraphQL layer

---

## Summary

The domain details API is well-structured with clear separation of concerns. The main optimization opportunities are:

1. **Client-side:** Reduce redundant queries by extracting counts from detailed queries
2. **Server-side:** Implement caching for frequently accessed data
3. **Architecture:** Consider batching similar queries (DataLoader pattern)

The `ipHoppingVisualization` query is correctly isolated as it serves a different purpose and uses historical data.
