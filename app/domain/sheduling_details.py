from typing import List, Optional

from pydantic import BaseModel


class SchedulingDetails(BaseModel):
    professional_name: Optional[str] = None
    specialty: Optional[str] = None
    date_preference: Optional[str] = None
    time_preference: Optional[str] = None
    specific_time: Optional[str] = None
    service_type: Optional[str] = "consulta"
    patient_name: Optional[str] = None
