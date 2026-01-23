# =========================================================
# CHATGPT-LIKE GROQ + STREAMLIT CHATBOT (STABLE FINAL)
# =========================================================

import streamlit as st
from groq import Groq
import json, csv, time
from datetime import datetime
from io import StringIO
import numpy as np
import faiss
from PyPDF2 import PdfReader

# ================= CONFIG =================
st.set_page_config(
    page_title="Chatbot",
    page_icon="💬",
    layout="wide"
)

DATA_FILE = "chat_store.json"

# ================= UI STYLE =================
def apply_chatgpt_style(dark=False):
    if dark:
        bg = "#0f1117"
        chat_bg = "#1e1f24"
        text = "#eaeaea"
        subtext = "#c9c9c9"
        code_bg = "#0b0f14"
        border = "#2a2b30"
    else:
        bg = "#ffffff"
        chat_bg = "#f7f7f8"
        text = "#1f1f1f"
        subtext = "#4a4a4a"
        code_bg = "#f1f1f1"
        border = "#dddddd"

    st.markdown(f"""
    <style>
    body, .stApp {{
        background: {bg};
        color: {text};
    }}

    .block-container {{
        max-width: 900px;
        padding-top: 2rem;
    }}

    .stChatMessage {{
        background: {chat_bg};
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid {border};
    }}

    .stMarkdown,
    .stMarkdown p,
    .stMarkdown li {{
        color: {text} !important;
        font-size: 16px;
        line-height: 1.65;
    }}

    pre {{
        background: {code_bg} !important;
        color: {text} !important;
        border-radius: 10px;
        padding: 14px;
        border: 1px solid {border};
        overflow-x: auto;
    }}

    code {{
        background: {code_bg};
        color: {text};
        padding: 3px 6px;
        border-radius: 6px;
    }}

    textarea, input {{
        border-radius: 12px !important;
        background: {chat_bg};
        color: {text};
        border: 1px solid {border};
    }}

    section[data-testid="stSidebar"] {{
        background: {chat_bg};
        border-right: 1px solid {border};
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= STORAGE =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= EMBEDDING =================
def embed(text):
    v = np.zeros(384, dtype="float32")
    for i, b in enumerate(text.encode()[:384]):
        v[i] = b
    return v

# ================= GROQ =================
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    username = st.text_input("Enter your name")
    if st.button("Start Chat") and username:
        st.session_state.user = username
        st.rerun()
    st.stop()

# ================= INIT =================
data = load_data()
user = st.session_state.user

if user not in data:
    data[user] = {}

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "dark" not in st.session_state:
    st.session_state.dark = False

apply_chatgpt_style(st.session_state.dark)

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("💬 Chats")

    for cid, chat in data[user].items():
        label = chat["title"]
        if st.button(label, key=cid):
            st.session_state.chat_id = cid
            st.rerun()

    if st.button("➕ New Chat"):
        cid = str(time.time())
        data[user][cid] = {
            "title": "New Chat",
            "messages": []
        }
        save_data(data)
        st.session_state.chat_id = cid
        st.rerun()

    st.divider()
    st.session_state.dark = st.toggle("🌙 Dark Mode", st.session_state.dark)

# ================= CHAT =================
if not st.session_state.chat_id:
    st.info("Create or select a chat")
    st.stop()

chat = data[user][st.session_state.chat_id]

for m in chat["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ================= FILE UPLOAD =================
uploaded = st.file_uploader(
    "Upload files",
    type=["pdf", "csv", "txt", "py", "html", "ipynb"],
    accept_multiple_files=True
)

context_text = ""
if uploaded:
    for f in uploaded:
        if f.type == "application/pdf":
            reader = PdfReader(f)
            for p in reader.pages:
                context_text += p.extract_text() or ""
        else:
            context_text += f.getvalue().decode("utf-8", errors="ignore")

    chunks = [context_text[i:i+500] for i in range(0, len(context_text), 500)]
    vecs = np.array([embed(c) for c in chunks])
    index = faiss.IndexFlatL2(384)
    index.add(vecs)
else:
    index = None
    chunks = []

# ================= INPUT =================
if prompt := st.chat_input("Ask anything..."):
    chat["messages"].append({"role": "user", "content": prompt})

    if chat["title"] == "New Chat":
        chat["title"] = prompt[:40]

    system = "You are a helpful ChatGPT-like assistant. Format answers clearly."

    messages = [{"role": "system", "content": system}]

    if index:
        q = embed(prompt).reshape(1, -1)
        _, i = index.search(q, 2)
        ctx = "\n".join(chunks[j] for j in i[0])
        messages.append({"role": "system", "content": f"Context:\n{ctx}"})

    messages.extend(chat["messages"][-6:])

    with st.chat_message("assistant"):
        out = ""
        box = st.empty()
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )
        for c in stream:
            if c.choices[0].delta.content:
                out += c.choices[0].delta.content
                box.markdown(out)

    chat["messages"].append({"role": "assistant", "content": out})
    save_data(data)
