# LLM logic will go here
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CODE_KEYWORDS = ["code", "python", "implement", "program"]

def wants_code(prompt: str) -> bool:
    return any(k in prompt.lower() for k in CODE_KEYWORDS)

def stream_groq(req):
    system_prompt = (
        "Explain clearly in plain text. Do NOT include code."
        if not wants_code(req.prompt)
        else "Provide correct and complete code with explanation."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *req.messages,
        {"role": "user", "content": req.prompt}
    ]

    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

