# ============================================================
# CHATGPT-LIKE GROQ + STREAMLIT (ALL FEATURES MERGED FINAL)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid, os, base64, requests
from datetime import datetime
from PyPDF2 import PdfReader
from PIL import Image
import docx2txt
import pandas as pd

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config("Chatbot", "💬", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
username TEXT PRIMARY KEY,
password TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS folders(
id TEXT PRIMARY KEY,
user TEXT,
name TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
user TEXT,
folder_id TEXT,
title TEXT,
pinned INTEGER,
created TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS messages(
id TEXT,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT)""")

conn.commit()

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------
def apply_style(dark):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text};}}
    .block-container{{max-width:900px}}
    .stChatMessage{{background:{chat};border-radius:12px;padding:14px;margin-bottom:10px}}
    pre{{background:#0b0f14;color:white;padding:12px;border-radius:10px}}
    .typing::after{{content:"▍";animation:blink 1s infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    </style>
    """,unsafe_allow_html=True)

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user=None

if not st.session_state.user:
    st.title("Login / Register")
    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    if st.button("Login"):
        if cur.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone():
            st.session_state.user=u
            st.rerun()
        else:
            st.error("Invalid")

    if st.button("Register"):
        cur.execute("INSERT INTO users VALUES (?,?)",(u,p))
        conn.commit()
        st.success("Registered")

    st.stop()

user=st.session_state.user

# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------
st.session_state.setdefault("chat_id",None)
st.session_state.setdefault("dark",False)
st.session_state.setdefault("mode","Auto")

apply_style(st.session_state.dark)

# ------------------------------------------------------------
# INTENT
# ------------------------------------------------------------
def detect_intent(p):
    p=p.lower()
    if "code" in p or "python" in p: return "CODE"
    if "explain" in p or "what is" in p: return "EXPLAIN"
    return "BOTH"

def system_prompt(intent):
    if intent=="CODE":
        return "Write ONLY code. No explanation."
    if intent=="EXPLAIN":
        return "Explain clearly. No code."
    return "Explain briefly then give code."

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    st.header(user)
    if st.button("Logout"):
        st.session_state.user=None
        st.rerun()

    st.session_state.dark=st.toggle("🌙 Dark Mode",st.session_state.dark)
    st.session_state.mode=st.selectbox("Answer Mode",
        ["Auto","Explain Only","Code Only","Explain + Code"])

    st.divider()

    # folders
    fname=st.text_input("New Folder")
    if st.button("Create Folder"):
        cur.execute("INSERT INTO folders VALUES (?,?,?)",
                    (str(uuid.uuid4()),user,fname))
        conn.commit()
        st.rerun()

    folders=cur.execute("SELECT id,name FROM folders WHERE user=?",(user,)).fetchall()

    for fid,name in folders:
        with st.expander(name):
            chats=cur.execute("SELECT id,title FROM chats WHERE folder_id=?",(fid,)).fetchall()
            for cid,title in chats:
                if st.button(title,key=cid):
                    st.session_state.chat_id=cid
                    st.rerun()

            if st.button("➕ New Chat",key=fid):
                cid=str(uuid.uuid4())
                cur.execute("INSERT INTO chats VALUES (?,?,?,?,?)",
                    (cid,user,fid,"New Chat",0,datetime.utcnow()))
                conn.commit()
                st.session_state.chat_id=cid
                st.rerun()

# ------------------------------------------------------------
# CHAT DISPLAY
# ------------------------------------------------------------
if not st.session_state.chat_id:
    st.info("Select or create a chat")
    st.stop()

history=cur.execute("""
SELECT role,content FROM messages
WHERE chat_id=? ORDER BY created
""",(st.session_state.chat_id,)).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ------------------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------------------
uploads=st.file_uploader("➕",accept_multiple_files=True)

def read_file(f):
    if f.type=="application/pdf":
        t=""
        r=PdfReader(f)
        for p in r.pages: t+=p.extract_text() or ""
        return t
    if f.type=="text/csv":
        return f.getvalue().decode()
    if f.type.startswith("image"):
        return "[Image uploaded]"
    return f.getvalue().decode(errors="ignore")

context=""
if uploads:
    for f in uploads:
        context+=read_file(f)

# ------------------------------------------------------------
# WEB SEARCH
# ------------------------------------------------------------
def web_search(q):
    return requests.get("https://duckduckgo.com/html/?q="+q).text[:3000]

# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------
if prompt:=st.chat_input("Ask anything..."):

    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()),st.session_state.chat_id,"user",prompt,datetime.utcnow()))
    conn.commit()

    if st.session_state.mode=="Auto":
        intent=detect_intent(prompt)
    elif st.session_state.mode=="Explain Only":
        intent="EXPLAIN"
    elif st.session_state.mode=="Code Only":
        intent="CODE"
    else:
        intent="BOTH"

    system=system_prompt(intent)

    msgs=[{"role":"system","content":system}]
    if context:
        msgs.append({"role":"system","content":"Context:"+context})

    msgs.append({"role":"user","content":prompt})

    with st.chat_message("assistant"):
        box=st.empty()
        out=""

        stream=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=msgs,
            stream=True)

        for ch in stream:
            if ch.choices[0].delta.content:
                out+=ch.choices[0].delta.content
                box.markdown(out+"<span class='typing'></span>",
                             unsafe_allow_html=True)

    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()),st.session_state.chat_id,"assistant",out,datetime.utcnow()))
    conn.commit()
