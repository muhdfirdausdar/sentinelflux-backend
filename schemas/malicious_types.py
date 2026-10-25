# schemas/malicious_types.py

from pydantic import BaseModel

class MaliciousTypeBase(BaseModel):
    name: str

    model_config = {
        "from_attributes": True  # enables conversion from ORM objects
    }

class MaliciousTypeOut(MaliciousTypeBase):
    id: int

    model_config = {
        "from_attributes": True
    }
