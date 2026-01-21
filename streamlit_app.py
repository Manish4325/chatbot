# 🚀 CHATGPT‑LIKE GROQ + STREAMLIT CHATBOT (FINAL UI MATCH)
# =======================================================
# GOAL:
# Make the Streamlit chatbot UI look & feel CLOSE to ChatGPT
# – clean white/light theme
# – subtle dark mode
# – centered chat
# – readable text & code
# – minimal sidebar

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

# ================= CHATGPT‑LIKE CSS =================
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

    /* Center chat */
    .block-container {{ max-width: 900px; padding-top: 2rem; }}

    /* Chat bubbles */
    .stChatMessage {{
        background: {chat_bg};
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
    }}

    /* Text */
    .stMarkdown p {{ font-size: 16px; line-height: 1.6; }}

    /* Code */
    pre, code {{
        background: {code_bg};
        color: {text};
        border-radius: 8px;
        font-size: 14px;
    }}

    /* Input */
    textarea, input {{
        border-radius: 12px !important;
        font-size: 16px;
    }}

    /* Sidebar */
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

# ================= INTENT =================
def wants_code(prompt: str, allow_code: bool) -> bool:
    if allow_code:
        return True
    keywords = ["code", "program", "python", "implement", "write"]
    return any(k in prompt.lower() for k in keywords)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    st.caption("ChatGPT‑style UI powered by Groq")
    username = st.text_input("Enter your name")
    if st.button("Start Chat") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

# ================= STATE =================
for k, v in {
    "messages": [],
    "dark": False,
    "faiss": None,
    "chunks": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

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

# ================= APPLY STYLE =================
apply_chatgpt_style(st.session_state.dark)

# ================= RAG =================
def embed(text):
    v = np.zeros(384, dtype="float32")
    for i, b in enumerate(text.encode()[:384]):
        v[i] = b
    return v

if uploaded:
    content = ""
    if uploaded.type == "application/pdf":
        r = PdfReader(uploaded)
        for p in r.pages:
            content += p.extract_text() or ""
    else:
        sio = StringIO(uploaded.getvalue().decode("utf-8"))
        for row in csv.reader(sio):
            content += " ".join(row)

    chunks = [content[i:i+500] for i in range(0, len(content), 500)]
    vecs = np.array([embed(c) for c in chunks])
    idx = faiss.IndexFlatL2(384)
    idx.add(vecs)
    st.session_state.faiss = idx
    st.session_state.chunks = chunks

# ================= CHAT =================
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    length_rule = {
        "Short": "Answer briefly.",
        "Medium": "Give a clear explanation.",
        "Long": "Give a detailed explanation."
    }[length]

    style_rule = {
        "ChatGPT": "Use friendly, conversational tone.",
        "Textbook": "Use structured academic explanation.",
        "Interview": "Answer concisely in 2–3 lines."
    }[style]

    code_rule = "Include code." if wants_code(prompt, allow_code) else "Do NOT include code."

    system = f"You are a helpful AI assistant. {length_rule} {style_rule} {code_rule}"

    context = [{"role": "system", "content": system}]

    if st.session_state.faiss:
        q = embed(prompt).reshape(1, -1)
        _, i = st.session_state.faiss.search(q, 2)
        ctx = "\n".join(st.session_state.chunks[j] for j in i[0])
        context.append({"role": "system", "content": f"Context:\n{ctx}"})

    context.extend(st.session_state.messages[-6:])

    with st.chat_message("assistant"):
        out = ""
        box = st.empty()
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=context,
            stream=True
        )
        for c in stream:
            if c.choices[0].delta.content:
                out += c.choices[0].delta.content
                box.markdown(out)

    st.session_state.messages.append({"role": "assistant", "content": out})

    try:
        with open("chat_logs.json", "a") as f:
            f.write(json.dumps({
                "user": st.session_state.user,
                "prompt": prompt,
                "response": out,
                "time": datetime.utcnow().isoformat()
            }) + "\n")
    except:
        pass
