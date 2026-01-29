# ============================================================
# CHATGPT STYLE STREAMLIT + GROQ CHATBOT (FINAL STABLE)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid
from datetime import datetime
from PyPDF2 import PdfReader
from PIL import Image
import pandas as pd
import requests
import faiss
from sentence_transformers import SentenceTransformer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")
MODEL = "llama-3.1-8b-instant"

# ---------------- API KEY ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Add GROQ_API_KEY in Streamlit secrets")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- EMBEDDINGS ----------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
username TEXT PRIMARY KEY,
password TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
user TEXT,
title TEXT,
pinned INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
chat_id TEXT,
role TEXT,
content TEXT
)
""")

conn.commit()

# ---------------- STYLE ----------------
def style(dark):
    bg="#0f1117" if dark else "#ffffff"
    chat="#1e1f24" if dark else "#f7f7f8"
    text="#eaeaea" if dark else "#1f1f1f"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text}}}
    .stChatMessage{{background:{chat};padding:12px;border-radius:10px}}
    pre{{background:#0b0f14;color:white;padding:12px;border-radius:8px}}
    </style>
    """,unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user=None

if not st.session_state.user:
    st.title("🔐 Login / Signup")

    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    if st.button("Login"):
        row=cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u,p)
        ).fetchone()
        if row:
            st.session_state.user=u
            st.rerun()
        else:
            st.error("Invalid login")

    if st.button("Signup"):
        try:
            cur.execute("INSERT INTO users VALUES(?,?)",(u,p))
            conn.commit()
            st.success("Account created")
        except:
            st.error("User exists")
    st.stop()

user=st.session_state.user

# ---------------- STATE ----------------
st.session_state.setdefault("chat_id",None)
st.session_state.setdefault("dark",False)
st.session_state.setdefault("vectors",[])
st.session_state.setdefault("texts",[])

style(st.session_state.dark)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.session_state.dark=st.toggle("🌙 Dark Mode")

    search=st.text_input("🔍 Search chats")

    chats=cur.execute(
        "SELECT id,title,pinned FROM chats WHERE user=?",
        (user,)
    ).fetchall()

    chats=[c for c in chats if search.lower() in c[1].lower()]

    for cid,title,pinned in chats:
        label=("⭐ " if pinned else "")+title
        if st.button(label,key=cid):
            st.session_state.chat_id=cid

    if st.button("➕ New Chat"):
        cid=str(uuid.uuid4())
        cur.execute(
            "INSERT INTO chats VALUES(?,?,0)",
            (cid,user,"New Chat")
        )
        conn.commit()
        st.session_state.chat_id=cid

    if st.session_state.chat_id:
        if st.button("📌 Pin / Unpin"):
            cur.execute(
                "UPDATE chats SET pinned=1-pinned WHERE id=?",
                (st.session_state.chat_id,)
            )
            conn.commit()

        if st.button("🗑 Delete"):
            cur.execute("DELETE FROM chats WHERE id=?",(st.session_state.chat_id,))
            cur.execute("DELETE FROM messages WHERE chat_id=?",(st.session_state.chat_id,))
            conn.commit()
            st.session_state.chat_id=None
            st.rerun()

        if st.button("⬇ Export PDF"):
            rows=cur.execute(
                "SELECT role,content FROM messages WHERE chat_id=?",
                (st.session_state.chat_id,)
            ).fetchall()

            c=canvas.Canvas("chat.pdf",pagesize=letter)
            y=750
            for r,t in rows:
                c.drawString(40,y,f"{r}: {t[:90]}")
                y-=20
            c.save()

            with open("chat.pdf","rb") as f:
                st.download_button("Download PDF",f,"chat.pdf")

# ---------------- CHAT ----------------
if not st.session_state.chat_id:
    st.info("Create or select a chat")
    st.stop()

history=cur.execute(
    "SELECT role,content FROM messages WHERE chat_id=?",
    (st.session_state.chat_id,)
).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- FILE UPLOAD ----------------
uploads=st.file_uploader(
"Upload files",
type=["pdf","txt","csv","png","jpg"],
accept_multiple_files=True
)

context=""

if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            reader=PdfReader(f)
            for p in reader.pages:
                txt=p.extract_text() or ""
                context+=txt
                st.session_state.texts.append(txt)
                st.session_state.vectors.append(embedder.encode(txt))
        elif f.type.startswith("image"):
            context+="[Image uploaded]"
        else:
            txt=f.getvalue().decode(errors="ignore")
            context+=txt
            st.session_state.texts.append(txt)
            st.session_state.vectors.append(embedder.encode(txt))

# ---------------- VECTOR SEARCH ----------------
def retrieve(q):
    if not st.session_state.vectors:
        return ""
    qv=embedder.encode(q)
    index=faiss.IndexFlatL2(len(qv))
    index.add(st.session_state.vectors)
    _,i=index.search([qv],1)
    return st.session_state.texts[i[0][0]]

# ---------------- INPUT ----------------
prompt=st.chat_input("Ask anything...")

if prompt:

    cur.execute(
        "INSERT INTO messages VALUES(?,?,?)",
        (st.session_state.chat_id,"user",prompt)
    )
    conn.commit()

    context+=retrieve(prompt)

    messages=[
        {"role":"system","content":"You are helpful AI."},
        {"role":"system","content":f"Context:\n{context}"}
    ]

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
            for ch in stream:
                if ch.choices[0].delta.content:
                    out+=ch.choices[0].delta.content
                    box.markdown(out)
        except:
            out="Groq API error"

    cur.execute(
        "INSERT INTO messages VALUES(?,?,?)",
        (st.session_state.chat_id,"assistant",out)
    )
    conn.commit()
