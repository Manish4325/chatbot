# 🚀 CHATGPT-LIKE GROQ + STREAMLIT CHATBOT (STABLE VERSION)

import streamlit as st
from groq import Groq
import time, json, csv
from io import StringIO
from datetime import datetime
from PyPDF2 import PdfReader
import numpy as np
import faiss

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Chatbot",
    page_icon="💬",
    layout="wide"
)

# ================= CHATGPT-LIKE CSS =================
def apply_chatgpt_style(dark=False):
    if dark:
        bg = "#0f1117"
        chat_bg = "#1e1f24"
        text = "#eaeaea"
        code_bg = "#0b0f14"
    else:
        bg = "#ffffff"
        chat_bg = "#f7f7f8"
        text = "#1f1f1f"
        code_bg = "#f1f1f1"

    st.markdown(f"""
    <style>
    body, .stApp {{ background:{bg}; color:{text}; }}

    .block-container {{
        max-width: 900px;
        padding-top: 2rem;
    }}

    .stChatMessage {{
        background: {chat_bg};
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 12px;
    }}

    .stMarkdown p {{
        font-size: 16px;
        line-height: 1.65;
        color: {text};
    }}

    pre {{
        background: {code_bg} !important;
        padding: 14px !important;
        border-radius: 10px;
        font-size: 14px;
        overflow-x: auto;
    }}

    code {{
        color: {text};
    }}

    textarea, input {{
        border-radius: 12px !important;
        font-size: 16px;
    }}

    section[data-testid="stSidebar"] {{
        background: {chat_bg};
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= GROQ =================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= HELPERS =================
def user_wants_code(prompt: str, allow_code: bool) -> bool:
    if allow_code:
        return True
    keywords = ["code", "program", "python", "implement", "write", "algorithm"]
    return any(k in prompt.lower() for k in keywords)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    st.caption("ChatGPT-style UI powered by Groq")
    username = st.text_input("Enter your name")
    if st.button("Start Chat") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

# ================= STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dark" not in st.session_state:
    st.session_state.dark = False
if "faiss" not in st.session_state:
    st.session_state.faiss = None
if "chunks" not in st.session_state:
    st.session_state.chunks = []

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("⚙️ Settings")
    st.session_state.dark = st.toggle("🌙 Dark mode", value=st.session_state.dark)
    allow_code = st.toggle("Allow code", value=False)
    length = st.selectbox("Answer length", ["Short", "Medium", "Long"], index=1)
    style = st.selectbox("Style", ["ChatGPT", "Textbook", "Interview"], index=0)

    uploaded = st.file_uploader("Upload PDF / CSV", type=["pdf", "csv"])

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

apply_chatgpt_style(st.session_state.dark)

# ================= SIMPLE RAG =================
def embed(text):
    v = np.zeros(384, dtype="float32")
    for i, b in enumerate(text.encode()[:384]):
        v[i] = b
    return v

if uploaded:
    content = ""
    if uploaded.type == "application/pdf":
        reader = PdfReader(uploaded)
        for p in reader.pages:
            content += p.extract_text() or ""
    else:
        sio = StringIO(uploaded.getvalue().decode("utf-8"))
        for row in csv.reader(sio):
            content += " ".join(row)

    chunks = [content[i:i+500] for i in range(0, len(content), 500)]
    vectors = np.array([embed(c) for c in chunks])

    index = faiss.IndexFlatL2(384)
    index.add(vectors)

    st.session_state.faiss = index
    st.session_state.chunks = chunks

# ================= CHAT DISPLAY =================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ================= CHAT INPUT =================
if prompt := st.chat_input("Ask anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    length_rule = {
        "Short": "Answer briefly in a few lines.",
        "Medium": "Give a clear explanation with examples if needed.",
        "Long": "Give a detailed explanation step by step."
    }[length]

    style_rule = {
        "ChatGPT": "Use a friendly, conversational tone.",
        "Textbook": "Use structured academic explanation.",
        "Interview": "Answer concisely like in an interview."
    }[style]

    wants_code = user_wants_code(prompt, allow_code)

    if wants_code:
        code_rule = (
            "If code is needed, first explain clearly, "
            "then provide the code in a separate section titled 'Code'."
        )
    else:
        code_rule = (
            "Do NOT include any code, code snippets, or pseudo-code. "
            "Only provide explanation in plain text."
        )

    system_prompt = f"""
You are a helpful AI assistant.
{length_rule}
{style_rule}
{code_rule}
"""

    messages = [{"role": "system", "content": system_prompt}]

    if st.session_state.faiss:
        q = embed(prompt).reshape(1, -1)
        _, idx = st.session_state.faiss.search(q, 2)
        ctx = "\n".join(st.session_state.chunks[i] for i in idx[0])
        messages.append({"role": "system", "content": f"Context:\n{ctx}"})

    messages.extend(st.session_state.messages[-6:])

    with st.chat_message("assistant"):
        output = ""
        placeholder = st.empty()

        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                output += chunk.choices[0].delta.content
                placeholder.markdown(output)

    st.session_state.messages.append({"role": "assistant", "content": output})

    try:
        with open("chat_logs.json", "a") as f:
            f.write(json.dumps({
                "user": st.session_state.user,
                "prompt": prompt,
                "response": output,
                "time": datetime.utcnow().isoformat()
            }) + "\n")
    except:
        pass
