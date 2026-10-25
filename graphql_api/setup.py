"""
GraphQL Setup and Configuration
Setup file that combines all queries and mutations into a unified schema
"""
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from .queries import (
    DomainQuery, SourceQuery, FastFluxQuery,
    IPQuery, NameserverQuery, MaliciousTypeQuery,
    IPGeolocationQuery, DomainIPConnectionQuery,
    DomainNameserverQuery, NameserverIPQuery,
    DomainIPMaliciousQuery,
    HistoryDomainQuery, HistoryFastFluxQuery,
    HistoryDomainIPConnectionQuery, HistoryDomainNameserverQuery,
    HistoryNameserverIPQuery, HistoryGeoIPQuery
)
from .multi_queries import DomainFluxLookupQuery, DomDetailSummaryQuery, ARecordInfoQuery, NSRecordInfoQuery, VisualizationQuery
from .mutations import DomainMutation


async def get_graphql_context(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Provide database session to GraphQL resolvers
    
    Add more context items here as needed:
    - Current user (for authentication)
    - Request object
    - Custom services/repositories
    """
    return {
        "db": db
    }


@strawberry.type
class Query(
    DomainQuery, 
    SourceQuery, 
    FastFluxQuery,
    IPQuery,
    NameserverQuery,
    MaliciousTypeQuery,
    IPGeolocationQuery,
    DomainIPConnectionQuery,
    DomainNameserverQuery,
    NameserverIPQuery,
    DomainIPMaliciousQuery,
    HistoryDomainQuery,
    HistoryFastFluxQuery,
    HistoryDomainIPConnectionQuery,
    HistoryDomainNameserverQuery,
    HistoryNameserverIPQuery,
    HistoryGeoIPQuery,
    DomainFluxLookupQuery,
    DomDetailSummaryQuery,
    ARecordInfoQuery,
    NSRecordInfoQuery,
    VisualizationQuery
):
    """
    Root Query type combining all entity queries
    - Domain queries: domains, domain operations
    - Source queries: sources, source operations
    - Fast Flux queries: fast_flux_analysis operations
    - IP queries: ips, ip operations
    - Nameserver queries: nameservers, nameserver operations
    - Malicious Type queries: malicious_types operations
    - IP Geolocation queries: ip_geolocations operations
    - Domain-IP Connection queries: domain_ip_connections operations
    - Domain-Nameserver queries: domain_nameservers operations
    - Nameserver-IP queries: nameserver_ips operations
    - Domain-IP Malicious queries: domain_ip_malicious operations
    - History Domain queries: history_domains operations
    - History Fast Flux queries: history_fast_flux_analysis operations
    - History Domain-IP Connection queries: history_domain_ip_connections operations
    - History Domain-Nameserver queries: history_domain_nameservers operations
    - History Nameserver-IP queries: history_nameserver_ips operations
    - History GeoIP queries: history_geoips operations
    - Multi-queries: Combined queries from multiple tables
      - domainFluxLookup: Domain fast flux lookup information
      - domDetailsSummary: Comprehensive domain details summary
      - aRecordInfo: A record information with IP reuse details
      - nsRecordInfo: NS record information with nameserver to IP details
      - ipHoppingVisualization: IP hopping visualization over time
    """
    pass


@strawberry.type
class Mutation(DomainMutation):
    """
    Root Mutation type combining all entity mutations
    Add more mutation classes here as you extend GraphQL to other tables
    """
    pass


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation
)


def create_graphql_router() -> GraphQLRouter:
    """
    Factory function to create a GraphQL router
    Returns a FastAPI router with GraphQL endpoint
    """
    return GraphQLRouter(
        schema,
        context_getter=get_graphql_context,
        path="/graphql"
    )
