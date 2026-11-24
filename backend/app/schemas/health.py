from pydantic import BaseModel
from typing import Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str
    database: str
    storage: str
    details: Optional[Dict[str, Any]] = None
