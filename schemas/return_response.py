from pydantic import BaseModel
from typing import Dict, Any
from enum import Enum

class ResponseStatus(str, Enum):
    good = "good"
    normal = "normal"
    error = "error"
    no_change = "no_change"

class ReturnResponse(BaseModel):
    status: ResponseStatus
    remark: str
    data: Dict[str, Any]