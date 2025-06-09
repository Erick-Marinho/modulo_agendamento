from pydantic import BaseModel


class ApiMedicalSpecialty(BaseModel):
    id: int
    especialidade: str
