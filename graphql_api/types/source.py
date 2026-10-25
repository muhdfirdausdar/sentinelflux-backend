"""
Source GraphQL Type
Type definition for Sources table
"""
import strawberry


@strawberry.type
class Source:
    """Source information - where domain was reported from"""
    id: int
    name: str
