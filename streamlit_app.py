# 🚀 CHATGPT-LIKE GROQ + STREAMLIT CHATBOT (STREAMLIT-CLOUD SAFE)

import streamlit as st
from groq import Groq
import json, os
import numpy as np
import pandas as pd
from io import StringIO
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
from PIL import Image
import faiss

# ================= CONFIG =================
st.set_page_config(page_title="Chatbot", page_icon="💬", layout="wide")

DATA_DIR = "chat_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= GROQ =================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= STORAGE =================
def user_file(user):
    return f"{DATA_DIR}/{user.lower()}.json"

def load_chats(user):
    if os.path.exists(user_file(user)):
        return json.load(open(user_file(user)))
    return {}

def save_chats(user, chats):
    json.dump(chats, open(user_file(user), "w"), indent=2)

# 🔧 Normalize old chat format
def normalize_chats(chats):
    normalized = {}
    for title, data in chats.items():
        if isinstance(data, list):
            normalized[title] = {
                "pinned": False,
                "created": datetime.utcnow().isoformat(),
                "messages": data
            }
        else:
            normalized[title] = data
    return normalized

# ================= EMBEDDING =================
def embed(text):
    v = np.zeros(384, dtype="float32")
    for i, b in enumerate(text.encode()[:384]):
        v[i] = b
    return v

# ================= FILE PARSING =================
def extract_text(file):
    ext = file.name.split(".")[-1].lower()

    try:
        if ext == "pdf":
            reader = PdfReader(file)
            return " ".join(p.extract_text() or "" for p in reader.pages)

        if ext == "docx":
            doc = Document(file)
            return " ".join(p.text for p in doc.paragraphs)

        if ext == "csv":
            return pd.read_csv(file).to_string()

        if ext in ["xlsx", "xls"]:
            return pd.read_excel(file).to_string()

        if ext == "html":
            soup = BeautifulSoup(file.read(), "html.parser")
            return soup.get_text()

        if ext in ["py", "ipynb", "txt"]:
            return file.read().decode("utf-8")

        if ext in ["png", "jpg", "jpeg"]:
            return (
                "[Image uploaded]\n"
                "OCR is disabled on Streamlit Cloud.\n"
                "Please describe the image or upload a text-based file."
            )

    except Exception as e:
        return f"[Could not read file: {e}]"

    return ""

# ================= STYLE =================
def apply_style(dark):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text};}}
    .block-container{{max-width:900px;}}
    .stChatMessage{{background:{chat};border-radius:12px;padding:12px;margin-bottom:10px;}}
    pre,code{{background:{code};border-radius:8px;font-size:14px;}}
    section[data-testid=stSidebar]{{background:{chat};}}
    </style>
    """, unsafe_allow_html=True)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    st.caption("ChatGPT-style UI powered by Groq")

    u = st.text_input("Enter your name")
    if st.button("Start Chat") and u:
        st.session_state.user = u
        raw = load_chats(u)
        st.session_state.chats = normalize_chats(raw)
        save_chats(u, st.session_state.chats)

        st.session_state.current = None
        st.session_state.dark = False
        st.session_state.faiss = None
        st.session_state.chunks = []
        st.rerun()

    st.stop()

# ================= STATE =================
for k, v in {
    "chats": {},
    "current": None,
    "dark": False,
    "faiss": None,
    "chunks": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("💬 Chats")
    search = st.text_input("🔍 Search")

    for title, meta in st.session_state.chats.items():
        if search.lower() in title.lower():
            icon = "⭐ " if meta.get("pinned") else ""
            if st.button(icon + title, use_container_width=True):
                st.session_state.current = title
                st.rerun()

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current = None
        st.rerun()

    st.divider()
    st.session_state.dark = st.toggle("🌙 Dark mode", st.session_state.dark)
    allow_code = st.toggle("Allow code", False)

    uploaded = st.file_uploader(
        "Upload files",
        type=["pdf","docx","csv","xlsx","html","py","ipynb","txt","png","jpg","jpeg"],
        accept_multiple_files=True
    )

apply_style(st.session_state.dark)

# ================= FILE RAG =================
if uploaded:
    full_text = ""
    for f in uploaded:
        full_text += extract_text(f)

    chunks = [full_text[i:i+500] for i in range(0, len(full_text), 500)]
    vecs = np.array([embed(c) for c in chunks])
    idx = faiss.IndexFlatL2(384)
    idx.add(vecs)

    st.session_state.faiss = idx
    st.session_state.chunks = chunks

# ================= CHAT DISPLAY =================
if st.session_state.current:
    for m in st.session_state.chats[st.session_state.current]["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# ================= CHAT =================
if prompt := st.chat_input("Ask anything..."):

    if not st.session_state.current:
        title = prompt[:50] + ("..." if len(prompt) > 50 else "")
        st.session_state.chats[title] = {
            "pinned": False,
            "created": datetime.utcnow().isoformat(),
            "messages": []
        }
        st.session_state.current = title

    messages = st.session_state.chats[st.session_state.current]["messages"]
    messages.append({"role": "user", "content": prompt})

    code_rule = (
        "Include code." if allow_code or
        any(k in prompt.lower() for k in ["code","python","implement","write"])
        else "Do NOT include code."
    )

    system = f"You are a helpful assistant. {code_rule}"

    context = [{"role": "system", "content": system}] + messages[-6:]

    if st.session_state.faiss:
        q = embed(prompt).reshape(1, -1)
        _, i = st.session_state.faiss.search(q, 2)
        ctx = "\n".join(st.session_state.chunks[j] for j in i[0])
        context.insert(1, {"role": "system", "content": f"Context:\n{ctx}"})

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

    messages.append({"role": "assistant", "content": out})
    save_chats(st.session_state.user, st.session_state.chats)
