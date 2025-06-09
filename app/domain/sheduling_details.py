from pydantic import BaseModel
from typing import Optional, List


class SchedulingDetails(BaseModel):
    professional_name: Optional[str] = None
    specialty: Optional[str] = None
    date_preference: Optional[str] = None
    time_preference: Optional[str] = None
    service_type: Optional[str] = None
