from pydantic import BaseModel, Field
from typing import List, Optional


# Copilot please check the ../query_sample/vis_domain?id.json


class ToDOMRecord(BaseModel):
    type: str
    domain_id: int
    domain: str
    ttl: int
    lowest_ttl: int
    highest_ttl: int

class ToNSRecord(BaseModel):
    type: str
    ns_id: int
    ns: str
    ttl: int
    lowest_ttl: int
    highest_ttl: int

class ToARecord(BaseModel):
    type: str
    ip_id: int
    ip: str
    ttl: int
    lowest_ttl: int
    highest_ttl: int



class VisARecord(BaseModel):
    type: str
    ip_id: int
    ip: str
    ttl: int
    lowest_ttl: int
    highest_ttl: int
    total_ip_to_domain_relations: int
    total_ip_to_ns_relations: int
    A_to_DOM_Records: List[ToDOMRecord]
    A_to_NS_Records: List[ToNSRecord]

class VisNSRecord(BaseModel):
    type: str
    ns_id: int
    ns: str
    ttl: int
    lowest_ttl: int
    highest_ttl: int
    total_ns_to_domain_relations: int
    total_ns_to_ip_relations: int
    NS_to_DOM_Records: List[ToDOMRecord]
    NS_to_A_Records: List[ToARecord]

class VisualisationDomainCentric(BaseModel):
    target_domain: str 
    target_domain_id: int 
    total_A_Records: int 
    total_NS_Records: int 
    A_Records: List[VisARecord]
    NS_Records: List[VisNSRecord]



