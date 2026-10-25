# schemas/nameserver.py

from pydantic import BaseModel
from typing import Optional



class NameserverBase(BaseModel):
    nameserver: str
    remarks: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class NameserverOut(NameserverBase):
    id: int

    model_config = {
        "from_attributes": True
    }
