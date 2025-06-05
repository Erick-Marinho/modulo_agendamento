from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from enum import Enum

class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error" 
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"

class ToolResult(BaseModel):
    status: ToolStatus
    message: str 
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

    class Config:
        use_enum_values = True