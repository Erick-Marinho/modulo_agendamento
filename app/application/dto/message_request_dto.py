from pydantic import BaseModel, Field, validator
from typing import Optional
from app.domain.message_domain import MessageDomain


class TextMessage(BaseModel):
    message: str = Field(..., description="The text of the message")


class MessageRequestPayload(BaseModel):
    message_id: str = Field(alias="messageId")
    phone_number: str = Field(alias="phone")
    text: TextMessage

    # Campos opcionais do WhatsApp que podem ser úteis
    chat_name: Optional[str] = Field(default=None, alias="chatName")
    sender_name: Optional[str] = Field(default=None, alias="senderName")
    instance_id: Optional[str] = Field(default=None, alias="instanceId")
    from_me: Optional[bool] = Field(default=False, alias="fromMe")
    is_group: Optional[bool] = Field(default=False, alias="isGroup")

    class Config:
        allow_population_by_field_name = True

    @property
    def message(self) -> str:
        """Retorna a mensagem de texto extraída do campo text"""
        return self.text.message

    @validator("text", pre=True)
    def validate_text(cls, v):
        return TextMessage(**v) if isinstance(v, dict) else v
