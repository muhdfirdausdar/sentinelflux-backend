from pydantic import BaseModel
from typing import Optional, List


class SFMetadataBase(BaseModel):
    total_unprocessed: int
    total_malicious: int
    total_benign: int
    total_digged: int
    total_singleflux: int
    total_doubleflux: int
    total_nameflux: int
    total_nameserver: int
    total_ipaddress: int
    total_sourcedata: int
    total_domain_indb: int
    last_updated: str