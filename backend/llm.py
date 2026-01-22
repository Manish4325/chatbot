# # LLM logic will go here
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a helpful assistant.

Rules:
- If the user asks to explain a topic → explain clearly, NO CODE.
- If the user asks for code → give code first, then a short explanation.
- If the user asks for both → do both.
- Never mix code and explanation unless explicitly asked.
- Keep answers clean and structured.
"""

def stream_groq(message: str):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
