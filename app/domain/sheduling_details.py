from pydantic import BaseModel
from typing import Optional, List

class SchedulingDetails(BaseModel):
    professional_name: Optional[str] = None
    specialty: Optional[str] = None
    date_preference: Optional[str] = None
    time_preference: Optional[str] = None
    service_type: Optional[str] = None

    def get_missing_fields(self) -> List[str]:
        missing_fields = []
        if not self.professional_name:
            missing_fields.append("nome do profissional")
        if not self.date_preference:
            missing_fields.append("data de preferência")
        if not self.time_preference:
            missing_fields.append("horário de preferência")
        if not self.service_type:
            missing_fields.append("tipo de serviço")
        if not self.specialty:
            missing_fields.append("especialidade")

        return missing_fields
