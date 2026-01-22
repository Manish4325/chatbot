from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from schemas import ChatRequest
from llm import stream_groq

app = FastAPI()

@app.post("/chat")
def chat(req: ChatRequest):
    return StreamingResponse(
        stream_groq(req.message),
        media_type="text/plain"
    )
