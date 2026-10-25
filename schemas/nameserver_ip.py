# schemas/nameserver_ip.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NameserverIPBase(BaseModel):
    nameserver_id: int
    ip_id: int
    ttl: int
    lowest_ttl: int
    lowest_ttl_time: datetime
    highest_ttl: int
    highest_ttl_time: datetime
    
    model_config = {
        "from_attributes": True
    }

class NameserverIPOut(NameserverIPBase):
    id: int
    first_seen: datetime
    last_seen: datetime

    model_config = {
        "from_attributes": True
    }
