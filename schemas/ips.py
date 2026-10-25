# schemas/ips.py

from pydantic import BaseModel, IPvAnyAddress
from datetime import datetime

class IPBase(BaseModel):
    ip_address: IPvAnyAddress
    first_seen: datetime
    last_seen: datetime

    model_config = {
        "from_attributes": True
    }

class IPOut(IPBase):
    id: int

    model_config = {
        "from_attributes": True
    }
