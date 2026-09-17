from typing import Optional

from pydantic import BaseModel


class ChatInput(BaseModel):

    message: str

    session_id: Optional[str] = "default"


class ChatOutput(BaseModel):

    response: str