# FULL FEATURED GROQ + STREAMLIT CHATBOT
# Features:
# - Free Groq LLM (no billing)
# - Streaming responses
# - Complete answers + continuation
# - PDF / CSV RAG chatbot
# - Save chat history
# - Rate limiting
# - Dark mode toggle
# - Resume / Interview bot mode

import streamlit as st
from groq import Groq
import time
from io import StringIO
from PyPDF2 import PdfReader
import csv

# ---------------- Page Config ----------------
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="centered")

# ---------------- Secrets ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY not found in Streamlit Secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- Rate Limiting ----------------
RATE_LIMIT_SECONDS = 2
if "last_call" not in st.session_state:
    st.session_state.last_call = 0

def rate_limited():
    now = time.time()
    if now - st.session_state.last_call < RATE_LIMIT_SECONDS:
        return True
    st.session_state.last_call = now
    return False

# ---------------- System Prompts ----------------
SYSTEM_PROMPTS = {
    "Normal": "You are a helpful AI assistant. Always give complete answers with examples.",
    "Interview": "You are an interview coach. Ask questions and evaluate answers.",
    "Resume": "You are a resume expert. Improve resumes and suggest changes."
}

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "Normal"

if "rag_context" not in st.session_state:
    st.session_state.rag_context = ""

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.mode = st.selectbox(
        "Chat Mode",
        ["Normal", "Interview", "Resume"]
    )

    dark = st.toggle("🌙 Dark Mode")
    if dark:
        st.markdown("<style>body{background-color:#0e1117;color:white}</style>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📄 Upload PDF / CSV", type=["pdf", "csv"])

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.rag_context = ""
        st.rerun()

# ---------------- RAG Processing ----------------
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = "".join(page.extract_text() for page in reader.pages)
        st.session_state.rag_context = text[:4000]
    elif uploaded_file.type == "text/csv":
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        reader = csv.reader(stringio)
        st.session_state.rag_context = " ".join(", ".join(row) for row in reader)[:4000]

# ---------------- Display Chat ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- Chat Input ----------------
if prompt := st.chat_input("Ask anything..."):
    if rate_limited():
        st.warning("⏳ Please wait before sending another message")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

        context = [
            {"role": "system", "content": SYSTEM_PROMPTS[st.session_state.mode]}
        ]

        if st.session_state.rag_context:
            context.append({
                "role": "system",
                "content": f"Use the following document context:\n{st.session_state.rag_context}"
            })

        context.extend(st.session_state.messages[-6:])

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

        st.session_state.messages.append({"role": "assistant", "content": full_response})
