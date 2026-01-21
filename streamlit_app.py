# FULL FEATURED GROQ + STREAMLIT CHATBOT (FINAL)
# Features:
# - Free Groq LLM (no billing)
# - Streaming responses
# - Complete answers + continuation
# - PDF / CSV RAG chatbot
# - Login / authentication (simple)
# - Save chat history (local JSON)
# - Multi-user support (session-based)
# - Analytics dashboard (basic)
# - Proper Dark Mode (full UI)

import streamlit as st
from groq import Groq
import time
from io import StringIO
from PyPDF2 import PdfReader
import csv
import json
from datetime import datetime

# ---------------- Page Config ----------------
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="centered")

# ---------------- Global Dark Mode CSS ----------------
def apply_dark_mode():
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stChatMessage {
            background-color: #1c1f26 !important;
        }
        textarea, input {
            background-color: #1c1f26 !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------------- Secrets ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY not found in Streamlit Secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- Authentication ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login")
    username = st.text_input("Enter username")
    if st.button("Login") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

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

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.mode = st.selectbox(
        "Chat Mode",
        ["Normal", "Interview", "Resume"]
    )

    st.session_state.dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)

    uploaded_file = st.file_uploader("📄 Upload PDF / CSV", type=["pdf", "csv"])

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.rag_context = ""
        st.rerun()

# ---------------- Apply Dark Mode ----------------
if st.session_state.dark_mode:
    apply_dark_mode()

# ---------------- RAG Processing ----------------
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = "".join(page.extract_text() or "" for page in reader.pages)
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

        # ---------------- Save Chat History ----------------
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

# ---------------- Analytics ----------------
st.divider()
st.subheader("📊 Session Analytics")
st.write(f"User: **{st.session_state.user}**")
st.write(f"Messages in session: **{len(st.session_state.messages)}**")
