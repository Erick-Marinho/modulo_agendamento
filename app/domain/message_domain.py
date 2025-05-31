from pydantic import BaseModel

class MessageDomain(BaseModel):
    message_id: str
    message: str
    phone_number: str
