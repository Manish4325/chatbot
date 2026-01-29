# ============================================================
# CHATGPT STYLE STREAMLIT + GROQ CHATBOT (ULTIMATE EDITION)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid
from datetime import datetime
from PyPDF2 import PdfReader
from PIL import Image
import pandas as pd
import speech_recognition as sr
import requests

# Optional OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")

MODEL = "llama-3.1-8b-instant"

# ---------------- API KEY ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Add GROQ_API_KEY in Streamlit secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
username TEXT PRIMARY KEY,
password TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS folders(
id TEXT PRIMARY KEY,
name TEXT,
user TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
folder_id TEXT,
user TEXT,
title TEXT,
created TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS messages(
id TEXT PRIMARY KEY,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS memory(
user TEXT,
content TEXT
)""")

conn.commit()

# ---------------- STYLE ----------------
def apply_style(dark):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text};}}
    .block-container{{max-width:900px}}
    .stChatMessage{{background:{chat};padding:14px;border-radius:12px}}
    pre{{background:{code};padding:12px;border-radius:8px}}
    .typing::after{{content:"▍";animation:blink 1s infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    </style>
    """, unsafe_allow_html=True)

# ---------------- AUTH ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login / Signup")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            row = cur.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (u,p)
            ).fetchone()

            if row:
                st.session_state.user=u
                st.rerun()
            else:
                st.error("Invalid login")

    with col2:
        if st.button("Signup"):
            try:
                cur.execute("INSERT INTO users VALUES(?,?)",(u,p))
                conn.commit()
                st.success("Account created")
            except:
                st.error("User exists")

    st.stop()

user = st.session_state.user

# ---------------- STATE ----------------
st.session_state.setdefault("chat_id",None)
st.session_state.setdefault("dark",False)

apply_style(st.session_state.dark)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.session_state.dark = st.toggle("🌙 Dark Mode",st.session_state.dark)

    if st.button("➕ New Folder"):
        fid=str(uuid.uuid4())
        cur.execute("INSERT INTO folders VALUES(?,?,?)",(fid,"My Chats",user))
        conn.commit()

    folders = cur.execute(
        "SELECT id,name FROM folders WHERE user=?",(user,)
    ).fetchall()

    for fid,name in folders:
        st.markdown(f"### 📁 {name}")

        if st.button("➕ New Chat",key=fid):
            cid=str(uuid.uuid4())
            cur.execute(
                "INSERT INTO chats VALUES(?,?,?,?,?)",
                (cid,fid,user,"New Chat",datetime.utcnow().isoformat())
            )
            conn.commit()
            st.session_state.chat_id=cid

        chats = cur.execute(
            "SELECT id,title FROM chats WHERE folder_id=?",(fid,)
        ).fetchall()

        for cid,title in chats:
            if st.button(title,key=cid):
                st.session_state.chat_id=cid

    if st.sidebar.button("⬇ Export Chat"):
        if st.session_state.chat_id:
            rows=cur.execute(
                "SELECT role,content FROM messages WHERE chat_id=?",
                (st.session_state.chat_id,)
            ).fetchall()
            txt=""
            for r,c in rows:
                txt+=f"{r.upper()}: {c}\n\n"
            st.download_button("Download",txt,"chat.txt")

# ---------------- CHAT ----------------
if not st.session_state.chat_id:
    st.info("Create or select a chat")
    st.stop()

history = cur.execute(
"SELECT role,content FROM messages WHERE chat_id=? ORDER BY created",
(st.session_state.chat_id,)
).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- FILE UPLOAD ----------------
uploads = st.file_uploader(
"Upload files/images",
type=["pdf","txt","csv","png","jpg","jpeg"],
accept_multiple_files=True
)

context=""

if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            reader=PdfReader(f)
            for p in reader.pages:
                context+=p.extract_text() or ""
        elif f.type.startswith("image"):
            if OCR_AVAILABLE:
                img=Image.open(f)
                context+=pytesseract.image_to_string(img)
            else:
                context+="[Image uploaded]"
        else:
            context+=f.getvalue().decode(errors="ignore")

# ---------------- WEB BROWSING ----------------
url = st.text_input("🌐 Paste website URL (optional)")
if url:
    try:
        r=requests.get(url,timeout=10)
        context+=r.text[:6000]
    except:
        st.warning("Could not fetch site")

# ---------------- VOICE INPUT ----------------
voice=None
audio=st.file_uploader("🎙 Upload voice",type=["wav","mp3"])
if audio:
    try:
        r=sr.Recognizer()
        with sr.AudioFile(audio) as src:
            aud=r.record(src)
            voice=r.recognize_google(aud)
    except:
        st.warning("Voice failed")

# ---------------- INPUT ----------------
prompt = st.chat_input("Ask anything...")
if voice:
    prompt=voice

if prompt:

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()),
                 st.session_state.chat_id,
                 "user",
                 prompt,
                 datetime.utcnow().isoformat()))
    conn.commit()

    # Save long term memory
    cur.execute("INSERT INTO memory VALUES(?,?)",(user,prompt))
    conn.commit()

    memories = cur.execute(
        "SELECT content FROM memory WHERE user=? ORDER BY rowid DESC LIMIT 5",
        (user,)
    ).fetchall()

    messages=[{"role":"system","content":"You are a helpful assistant."}]

    if memories:
        mem="\n".join([m[0] for m in memories])
        messages.append({"role":"system","content":"User memory:\n"+mem})

    if context:
        messages.append({"role":"system","content":"Context:\n"+context})

    messages.extend([{"role":r,"content":c} for r,c in history[-6:]])
    messages.append({"role":"user","content":prompt})

    with st.chat_message("assistant"):
        box=st.empty()
        out=""

        try:
            stream=client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    out+=chunk.choices[0].delta.content
                    box.markdown(out+"▍")

        except:
            out="Groq API error. Check key or model."

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()),
                 st.session_state.chat_id,
                 "assistant",
                 out,
                 datetime.utcnow().isoformat()))
    conn.commit()
