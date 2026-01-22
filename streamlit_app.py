# 🚀 CHATGPT-LIKE GROQ + STREAMLIT CHATBOT (WITH CHAT HISTORY & PERSISTENCE)

import streamlit as st
from groq import Groq
import json, os, csv
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

# ================= STORAGE =================
DATA_DIR = "chat_data"
os.makedirs(DATA_DIR, exist_ok=True)

def user_file(username):
    return os.path.join(DATA_DIR, f"{username.lower()}.json")

def load_user_chats(username):
    path = user_file(username)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_user_chats(username, chats):
    with open(user_file(username), "w") as f:
        json.dump(chats, f, indent=2)

# ================= CSS =================
def apply_chatgpt_style(dark=False):
    bg = "#0f1117" if dark else "#ffffff"
    chat_bg = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code_bg = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body, .stApp {{ background:{bg}; color:{text}; }}
    .block-container {{ max-width: 900px; padding-top: 2rem; }}
    .stChatMessage {{ background:{chat_bg}; border-radius:12px; padding:12px; }}
    pre, code {{ background:{code_bg}; border-radius:8px; }}
    textarea {{ border-radius:12px; }}
    section[data-testid="stSidebar"] {{ background:{chat_bg}; }}
    </style>
    """, unsafe_allow_html=True)

# ================= GROQ =================
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    st.caption("ChatGPT-style UI powered by Groq")
    username = st.text_input("Enter your name")
    if st.button("Start Chat") and username:
        st.session_state.user = username
        st.session_state.chats = load_user_chats(username)
        st.session_state.current_chat = None
        st.rerun()
    st.stop()

# ================= STATE =================
if "chats" not in st.session_state:
    st.session_state.chats = load_user_chats(st.session_state.user)

if "current_chat" not in st.session_state:
    st.session_state.current_chat = None

if "dark" not in st.session_state:
    st.session_state.dark = False

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("💬 Chats")

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_chat = None
        st.rerun()

    for title in st.session_state.chats:
        if st.button(title, use_container_width=True):
            st.session_state.current_chat = title
            st.rerun()

    st.divider()
    st.session_state.dark = st.toggle("🌙 Dark mode", st.session_state.dark)
    allow_code = st.toggle("Allow code", False)
    length = st.selectbox("Answer length", ["Short", "Medium", "Long"], 1)
    style = st.selectbox("Style", ["ChatGPT", "Textbook", "Interview"], 0)

# ================= APPLY STYLE =================
apply_chatgpt_style(st.session_state.dark)

# ================= CHAT DISPLAY =================
if st.session_state.current_chat:
    for msg in st.session_state.chats[st.session_state.current_chat]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ================= PROMPT =================
if prompt := st.chat_input("Ask anything..."):

    # Create new chat title if needed
    if not st.session_state.current_chat:
        title = prompt[:40] + ("..." if len(prompt) > 40 else "")
        st.session_state.chats[title] = []
        st.session_state.current_chat = title

    chat = st.session_state.chats[st.session_state.current_chat]
    chat.append({"role": "user", "content": prompt})

    rules = {
        "Short": "Answer briefly.",
        "Medium": "Give a clear explanation.",
        "Long": "Give a detailed explanation."
    }[length]

    style_rule = {
        "ChatGPT": "Use friendly tone.",
        "Textbook": "Use structured academic style.",
        "Interview": "Answer concisely."
    }[style]

    code_rule = "Include code." if allow_code else "Do NOT include code unless asked."

    system = f"You are a helpful assistant. {rules} {style_rule} {code_rule}"

    messages = [{"role": "system", "content": system}] + chat[-6:]

    with st.chat_message("assistant"):
        output = ""
        box = st.empty()
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )
        for c in stream:
            if c.choices[0].delta.content:
                output += c.choices[0].delta.content
                box.markdown(output)

    chat.append({"role": "assistant", "content": output})
    save_user_chats(st.session_state.user, st.session_state.chats)
