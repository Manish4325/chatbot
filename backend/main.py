# from fastapi import FastAPI

# app = FastAPI()

# @app.get("/")
# def health():
#     return {"status": "Backend is running"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from schemas import ChatRequest
from llm import stream_groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
def chat(req: ChatRequest):
    return StreamingResponse(
        stream_groq(req.message),
        media_type="text/plain"
    )

@app.get("/")
def health():
    return {"status": "Backend running"}
