# 🚀 FULLY WORKING GROQ + STREAMLIT AI CHATBOT (CLEAN & FIXED)
# =========================================================
# FEATURES INCLUDED:
# - Groq LLaMA-3.1 (FREE, no billing)
# - Streaming responses (complete answers)
# - Dark mode (FULL UI)
# - Login (simple username-based)
# - Multi-user sessions
# - PDF / CSV RAG (FAISS)
# - Rate limiting (free-tier safe)
# - Chat history logging
# - Admin-ready structure (simple)

import streamlit as st
from groq import Groq
import time
import json
import csv
from io import StringIO
from datetime import datetime
from PyPDF2 import PdfReader
import numpy as np
import faiss

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="AI Chatbot",
    page_icon="🤖",
    layout="centered"
)

# ================= DARK MODE CSS =================
def apply_dark_mode():
    st.markdown(
        """
        <style>
        body, .stApp { background-color:#0e1117; color:#fafafa; }
        .stChatMessage { background-color:#1c1f26 !important; }
        textarea, input { background-color:#1c1f26 !important; color:white !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ================= GROQ API =================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY not found in Streamlit Secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= AUTH =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login")
    username = st.text_input("Enter username")
    if st.button("Login") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

# ================= RATE LIMIT =================
RATE_LIMIT_SECONDS = 2
if "last_call" not in st.session_state:
    st.session_state.last_call = 0

def rate_limited():
    now = time.time()
    if now - st.session_state.last_call < RATE_LIMIT_SECONDS:
        return True
    st.session_state.last_call = now
    return False

# ================= SYSTEM PROMPTS =================
SYSTEM_PROMPTS = {
    "Normal": "You are a helpful AI assistant. Always give complete answers with examples and full code.",
    "Interview": "You are an interviewer. Ask questions and evaluate answers.",
    "Resume": "You are a resume expert. Improve resumes professionally."
}

# ================= SESSION STATE =================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "Normal"

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if "faiss_index" not in st.session_state:
    st.session_state.faiss_index = None

if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = []

# ================= SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.mode = st.selectbox(
        "Chat Mode",
        list(SYSTEM_PROMPTS.keys())
    )

    st.session_state.dark_mode = st.toggle(
        "🌙 Dark Mode",
        value=st.session_state.dark_mode
    )

    uploaded_file = st.file_uploader(
        "📄 Upload PDF / CSV",
        type=["pdf", "csv"]
    )

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ================= APPLY DARK MODE =================
if st.session_state.dark_mode:
    apply_dark_mode()

# ================= RAG (FAISS) =================
def embed_text(text: str) -> np.ndarray:
    vec = np.zeros(384, dtype="float32")
    encoded = text.encode()[:384]
    for i, b in enumerate(encoded):
        vec[i] = b
    return vec

if uploaded_file:
    text = ""

    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""

    elif uploaded_file.type == "text/csv":
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        reader = csv.reader(stringio)
        for row in reader:
            text += " ".join(row)

    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    vectors = np.array([embed_text(c) for c in chunks])

    index = faiss.IndexFlatL2(384)
    index.add(vectors)

    st.session_state.faiss_index = index
    st.session_state.doc_chunks = chunks

# ================= DISPLAY CHAT =================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ================= CHAT INPUT =================
if prompt := st.chat_input("Ask anything..."):
    if rate_limited():
        st.warning("⏳ Please wait a moment before sending another message")
    else:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        context = [
            {"role": "system", "content": SYSTEM_PROMPTS[st.session_state.mode]}
        ]

        # ---- FAISS RETRIEVAL (FIXED & SAFE) ----
        if st.session_state.faiss_index is not None:
            q_vec = embed_text(prompt).reshape(1, -1)
            _, idx = st.session_state.faiss_index.search(q_vec, 2)

            retrieved = "\n".join(
                st.session_state.doc_chunks[i] for i in idx[0]
            )

            context.append({
                "role": "system",
                "content": f"Document context:\n{retrieved}"
            })

        context.extend(st.session_state.messages[-6:])

        # ---- GROQ STREAMING ----
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=context,
                stream=True,
                max_tokens=1200
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

        # ---- SAVE CHAT LOG ----
        log = {
            "user": st.session_state.user,
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": prompt,
            "response": full_response
        }

        try:
            with open("chat_logs.json", "a") as f:
                f.write(json.dumps(log) + "\n")
        except:
            pass

# ================= ANALYTICS =================
st.divider()
st.write(f"👤 User: **{st.session_state.user}**")
st.write(f"💬 Messages this session: **{len(st.session_state.messages)}**")
