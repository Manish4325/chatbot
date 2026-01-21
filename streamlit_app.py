# 🚀 FINAL POLISHED GROQ + STREAMLIT AI CHATBOT (UX FIXED)
# ======================================================
# FIXES & FEATURES:
# ✔ Intent-aware answers (no code unless asked)
# ✔ UI toggles: Allow Code / Answer Length / Mode
# ✔ Proper Dark Mode (text + code readable)
# ✔ Streaming responses
# ✔ PDF / CSV RAG (FAISS)
# ✔ Login, multi-user, rate limiting

import streamlit as st
from groq import Groq
import time, json, csv
from io import StringIO
from datetime import datetime
from PyPDF2 import PdfReader
import numpy as np
import faiss

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")

# ================= DARK MODE CSS =================
def apply_dark_mode():
    st.markdown(
        """
        <style>
        body, .stApp {
            background-color: #0e1117;
            color: #e6e6e6;
        }
        .stChatMessage {
            background-color: #161a23 !important;
            border-radius: 10px;
        }
        /* Explanation text */
        .stMarkdown p, .stMarkdown li {
            color: #e6e6e6 !important;
            line-height: 1.6;
        }
        /* Code blocks */
        pre, code {
            background-color: #0b0f14 !important;
            color: #f8f8f2 !important;
            border-radius: 8px;
        }
        textarea, input {
            background-color: #161a23 !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ================= INTENT DETECTION =================
def wants_code(user_prompt: str, allow_code_toggle: bool) -> bool:
    if allow_code_toggle:
        return True
    keywords = ["code", "program", "python", "implement", "implementation", "write"]
    return any(k in user_prompt.lower() for k in keywords)

# ================= GROQ =================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing")
    st.stop()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= AUTH =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login")
    username = st.text_input("Username")
    if st.button("Login") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

# ================= RATE LIMIT =================
if "last_call" not in st.session_state:
    st.session_state.last_call = 0

def rate_limited():
    now = time.time()
    if now - st.session_state.last_call < 2:
        return True
    st.session_state.last_call = now
    return False

# ================= SESSION STATE =================
for k, v in {
    "messages": [],
    "dark": False,
    "faiss_index": None,
    "doc_chunks": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= SIDEBAR =================
with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark)
    allow_code = st.toggle("💻 Allow Code", value=False)

    answer_style = st.selectbox(
        "Answer Length",
        ["Short", "Medium", "Long"],
        index=1
    )

    mode = st.selectbox(
        "Explanation Style",
        ["Academic", "Practical", "Interview"],
        index=0
    )

    uploaded_file = st.file_uploader("📄 Upload PDF / CSV", type=["pdf", "csv"])

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ================= APPLY DARK MODE =================
if st.session_state.dark:
    apply_dark_mode()

# ================= RAG =================
def embed_text(text: str) -> np.ndarray:
    vec = np.zeros(384, dtype="float32")
    for i, b in enumerate(text.encode()[:384]):
        vec[i] = b
    return vec

if uploaded_file:
    text = ""
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    else:
        sio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        for row in csv.reader(sio):
            text += " ".join(row)

    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    vectors = np.array([embed_text(c) for c in chunks])

    index = faiss.IndexFlatL2(384)
    index.add(vectors)

    st.session_state.faiss_index = index
    st.session_state.doc_chunks = chunks

# ================= DISPLAY =================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ================= CHAT =================
if prompt := st.chat_input("Ask anything..."):
    if rate_limited():
        st.warning("⏳ Please wait a moment")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

        # ----- SYSTEM INSTRUCTION -----
        length_rule = {
            "Short": "Answer briefly in 3-4 lines.",
            "Medium": "Give a clear explanation with key points.",
            "Long": "Give a detailed and structured explanation."
        }[answer_style]

        mode_rule = {
            "Academic": "Use formal academic language.",
            "Practical": "Explain with real-world intuition.",
            "Interview": "Answer concisely like in an interview (2-3 lines)."
        }[mode]

        if wants_code(prompt, allow_code):
            code_rule = "Include code only if it helps the answer."
        else:
            code_rule = "DO NOT include any code or programming examples."

        system_instruction = (
            f"You are a helpful AI assistant. {length_rule} {mode_rule} {code_rule}"
        )

        context = [{"role": "system", "content": system_instruction}]

        if st.session_state.faiss_index is not None:
            q_vec = embed_text(prompt).reshape(1, -1)
            _, idx = st.session_state.faiss_index.search(q_vec, 2)
            retrieved = "\n".join(st.session_state.doc_chunks[i] for i in idx[0])
            context.append({"role": "system", "content": f"Document context:\n{retrieved}"})

        context.extend(st.session_state.messages[-6:])

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=context,
                stream=True,
                max_tokens=1200
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full += chunk.choices[0].delta.content
                    placeholder.markdown(full)

        st.session_state.messages.append({"role": "assistant", "content": full})

        try:
            with open("chat_logs.json", "a") as f:
                f.write(json.dumps({
                    "user": st.session_state.user,
                    "time": datetime.utcnow().isoformat(),
                    "prompt": prompt,
                    "response": full
                }) + "\n")
        except:
            pass

# ================= FOOTER =================
st.divider()
st.write(f"👤 User: **{st.session_state.user}**")
st.write(f"💬 Messages this session: **{len(st.session_state.messages)}**")
