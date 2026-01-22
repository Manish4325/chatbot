# LLM logic will go here
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def wants_code(prompt: str) -> bool:
    keywords = [
        "code", "program", "implement", "write", "python",
        "java", "c++", "algorithm", "function"
    ]
    return any(k in prompt.lower() for k in keywords)


def stream_groq(prompt: str):
    """
    Generator function that streams Groq response safely
    """

    if wants_code(prompt):
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

    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
