from pydantic import BaseModel
from typing import List, Optional
from app.domain.entities.medical_specialty import ApiMedicalSpecialty

class ApiMedicalProfessional(BaseModel):
    id: int
    nome: str
    numeroConselho: Optional[str] = None
    ufConselho: Optional[str] = None
    conselho: Optional[str] = None 
    prefixo: Optional[str] = None  
    cpf: Optional[str] = None 
    especialidades: List[ApiMedicalSpecialty]