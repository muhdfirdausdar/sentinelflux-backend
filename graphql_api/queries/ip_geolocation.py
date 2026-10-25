"""
IP Geolocation Query Resolvers
All query operations for IPGeolocation table
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..types.ip_geolocation import IPGeolocation

# Import model
from models.ip_geolocation import IPGeolocation as IPGeolocationModel


@strawberry.type
class IPGeolocationQuery:
    """Query operations for IPGeolocation table"""
    
    @strawberry.field
    async def ip_geolocations(
        self,
        info: Info,
        ip_id: Optional[int] = None,
        country: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[IPGeolocation]:
        """
        Get IP geolocations with optional filtering
        
        GraphQL Query Examples:
        
        # Get all geolocations
        {
          ipGeolocations(limit: 10) {
            id
            ipId
            country
            continent
            asn
            aso
          }
        }
        
        # Get geolocations for specific IP
        {
          ipGeolocations(ipId: 1) {
            country
            continent
            latitudeLongitude
            asn
          }
        }
        
        # Filter by country
        {
          ipGeolocations(country: "US", limit: 10) {
            ipId
            country
            aso
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(IPGeolocationModel)
        
        # Apply filters
        if ip_id:
            query = query.where(IPGeolocationModel.ip_id == ip_id)
        if country:
            query = query.where(IPGeolocationModel.country == country)
        
        query = query.order_by(desc(IPGeolocationModel.last_seen)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        geos = result.scalars().all()
        
        return [
            IPGeolocation(
                id=g.id,
                ip_id=g.ip_id,
                continent=g.continent,
                country=g.country,
                latitude_longitude=g.latitude_longitude,
                asn=g.asn,
                aso=g.aso,
                first_seen=g.first_seen,
                last_seen=g.last_seen
            )
            for g in geos
        ]
    
    @strawberry.field
    async def ip_geolocation_by_id(
        self,
        info: Info,
        id: int
    ) -> Optional[IPGeolocation]:
        """
        Get a specific IP geolocation by ID
        
        GraphQL Query Examples:
        
        # Get geolocation by ID
        {
          ipGeolocationById(id: 1) {
            id
            ipId
            country
            continent
            asn
            aso
          }
        }
        """
        db: AsyncSession = info.context["db"]
        
        query = select(IPGeolocationModel).where(IPGeolocationModel.id == id)
        result = await db.execute(query)
        geo = result.scalar_one_or_none()
        
        if not geo:
            return None
        
        return IPGeolocation(
            id=geo.id,
            ip_id=geo.ip_id,
            continent=geo.continent,
            country=geo.country,
            latitude_longitude=geo.latitude_longitude,
            asn=geo.asn,
            aso=geo.aso,
            first_seen=geo.first_seen,
            last_seen=geo.last_seen
        )
