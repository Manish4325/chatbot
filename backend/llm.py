# LLM logic will go here
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CODE_KEYWORDS = ["code", "python", "implement", "program"]

def wants_code(prompt: str) -> bool:
    return any(k in prompt.lower() for k in CODE_KEYWORDS)

if wants_code(req.prompt):
    system_prompt = (
        "You are a helpful programming assistant.\n\n"
        "RULES:\n"
        "1. First give a SHORT explanation (2–4 lines max).\n"
        "2. Then give the COMPLETE code inside a Markdown code block.\n"
        "3. Do NOT mix explanation and code.\n"
        "4. Do NOT add extra text after the code.\n"
    )
else:
    system_prompt = (
        "You are a helpful assistant.\n\n"
        "RULES:\n"
        "1. Answer ONLY in clear explanation.\n"
        "2. Use headings and bullet points if helpful.\n"
        "3. Do NOT include code.\n"
        "4. Keep the explanation structured and readable.\n"
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

