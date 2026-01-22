# Pydantic schemas will go here
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

