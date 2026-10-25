"""
Malicious Type GraphQL Type
Type definition for MaliciousTypes lookup table
"""
import strawberry


@strawberry.type
class MaliciousType:
    """Malicious type lookup"""
    id: int
    name: str
