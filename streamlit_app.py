# ============================================================
# CHATGPT STYLE STREAMLIT + GROQ CHATBOT (ADVANCED FINAL)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid, os
from datetime import datetime
from PyPDF2 import PdfReader
from PIL import Image
import pandas as pd
import speech_recognition as sr

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")

# ---------------- API KEY ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Add GROQ_API_KEY in Streamlit secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODEL = "llama-3.1-8b-instant"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

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

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user=None

if not st.session_state.user:
    st.title("💬 Chatbot")
    name=st.text_input("Enter your name")
    if st.button("Start") and name:
        st.session_state.user=name
        st.rerun()
    st.stop()

user=st.session_state.user

# ---------------- STATE ----------------
st.session_state.setdefault("chat_id",None)
st.session_state.setdefault("folder_id",None)
st.session_state.setdefault("dark",False)

apply_style(st.session_state.dark)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.session_state.dark=st.toggle("🌙 Dark mode",st.session_state.dark)

    if st.button("➕ New Folder"):
        fid=str(uuid.uuid4())
        cur.execute("INSERT INTO folders VALUES(?,?,?)",(fid,"My Chats",user))
        conn.commit()

    folders=cur.execute("SELECT id,name FROM folders WHERE user=?",(user,)).fetchall()

    for fid,name in folders:
        st.markdown(f"### 📁 {name}")

        if st.button("➕ New Chat",key=f"new{fid}"):
            cid=str(uuid.uuid4())
            cur.execute("INSERT INTO chats VALUES(?,?,?,?,?)",
                        (cid,fid,user,"New Chat",datetime.utcnow().isoformat()))
            conn.commit()
            st.session_state.chat_id=cid

        chats=cur.execute("SELECT id,title FROM chats WHERE folder_id=?",(fid,)).fetchall()
        for cid,title in chats:
            if st.button(title,key=cid):
                st.session_state.chat_id=cid

# ---------------- HISTORY ----------------
if not st.session_state.chat_id:
    st.info("Create or select a chat")
    st.stop()

history=cur.execute(
"SELECT role,content FROM messages WHERE chat_id=? ORDER BY created",
(st.session_state.chat_id,)
).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- UPLOADS ----------------
uploads=st.file_uploader(
"Upload files or images",
type=["pdf","csv","txt","png","jpg","jpeg"],
accept_multiple_files=True)

context=""

if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            reader=PdfReader(f)
            for p in reader.pages:
                context+=p.extract_text() or ""
        elif f.type.startswith("image"):
            context+="\n[User uploaded image for analysis]"
        else:
            context+=f.getvalue().decode(errors="ignore")

# ---------------- VOICE INPUT ----------------
voice=None
audio=st.file_uploader("🎙 Upload voice",type=["wav","mp3"])
if audio:
    r=sr.Recognizer()
    with sr.AudioFile(audio) as source:
        audio_data=r.record(source)
        voice=r.recognize_google(audio_data)

# ---------------- INPUT ----------------
prompt=st.chat_input("Ask anything...")
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

    messages=[{"role":"system","content":"You are helpful."}]
    if context:
        messages.append({"role":"system","content":context})

    messages.extend([{"role":r,"content":c} for r,c in history[-6:]])

    with st.chat_message("assistant"):
        box=st.empty()
        out=""

        stream=client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                out+=chunk.choices[0].delta.content
                box.markdown(out+"▍")

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()),
                 st.session_state.chat_id,
                 "assistant",
                 out,
                 datetime.utcnow().isoformat()))
    conn.commit()

# ---------------- EXPORT ----------------
if st.sidebar.button("⬇ Export Chat"):
    text=""
    for r,c in history:
        text+=f"{r.upper()}: {c}\n\n"
    st.sidebar.download_button("Download",text,"chat.txt")

