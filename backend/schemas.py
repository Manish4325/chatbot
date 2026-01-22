# Pydantic schemas will go here
# from pydantic import BaseModel
# from typing import List

# class Message(BaseModel):
#     role: str
#     content: str

# class ChatRequest(BaseModel):
#     prompt: str
#     messages: List[Message]
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
