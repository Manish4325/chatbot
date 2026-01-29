# ============================================================
# CHATGPT STYLE STREAMLIT + GROQ CHATBOT (DEBUG SAFE VERSION)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid
from datetime import datetime
from PyPDF2 import PdfReader

st.set_page_config("Chatbot", "💬", layout="wide")

# ---------------- CHECK SECRET ----------------
st.write("Groq key loaded:", st.secrets.get("GROQ_API_KEY","NONE")[:5])

if "GROQ_API_KEY" not in st.secrets:
    st.error("GROQ_API_KEY missing in secrets")
    st.stop()

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
user TEXT,
title TEXT,
pinned INTEGER,
created TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
id TEXT PRIMARY KEY,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT
)
""")

conn.commit()

# ---------------- GROQ ----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- STYLE ----------------
def style():
    st.markdown("""
    <style>
    .block-container{max-width:900px}
    .stChatMessage{padding:14px;border-radius:12px;background:#f7f7f8}
    </style>
    """,unsafe_allow_html=True)

style()

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user=None

if not st.session_state.user:
    st.title("Chatbot")
    name=st.text_input("Enter name")
    if st.button("Start") and name:
        st.session_state.user=name
        st.rerun()
    st.stop()

user=st.session_state.user
st.session_state.setdefault("chat_id",None)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    if st.button("➕ New Chat"):
        cid=str(uuid.uuid4())
        cur.execute("INSERT INTO chats VALUES(?,?,?,?,?)",
            (cid,user,"New Chat",0,datetime.utcnow().isoformat()))
        conn.commit()
        st.session_state.chat_id=cid
        st.rerun()

    chats=cur.execute(
        "SELECT id,title FROM chats WHERE user=? ORDER BY created DESC",
        (user,)
    ).fetchall()

    for cid,title in chats:
        if st.button(title,key=cid):
            st.session_state.chat_id=cid
            st.rerun()

# ---------------- CHAT ----------------
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

# ---------------- FILE UPLOAD ----------------
files=st.file_uploader("Attach files",accept_multiple_files=True)
context=""
if files:
    for f in files:
        if f.type=="application/pdf":
            reader=PdfReader(f)
            for p in reader.pages:
                context+=p.extract_text() or ""
        else:
            context+=f.getvalue().decode(errors="ignore")

# ---------------- INPUT ----------------
if prompt:=st.chat_input("Ask anything"):

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()),
         st.session_state.chat_id,
         "user",
         prompt,
         datetime.utcnow().isoformat()))
    conn.commit()

    messages=[{"role":"user","content":prompt}]
    if context:
        messages.insert(0,{"role":"system","content":f"Context:\n{context}"})

    try:
        resp=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        answer=resp.choices[0].message.content
    except Exception as e:
        st.error(f"Groq Error: {e}")
        st.stop()

    with st.chat_message("assistant"):
        st.markdown(answer)

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()),
         st.session_state.chat_id,
         "assistant",
         answer,
         datetime.utcnow().isoformat()))
    conn.commit()
