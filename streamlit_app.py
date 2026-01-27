# ============================================================
# CHATGPT-LIKE GROQ + STREAMLIT (IMAGE + WEB + USERS + FOLDERS)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid, requests
from datetime import datetime
from PyPDF2 import PdfReader
from PIL import Image
import base64

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- DATABASE ----------------
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
created TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS messages(
id TEXT,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT)""")

conn.commit()

# ---------------- STYLE ----------------
def style():
    st.markdown("""
    <style>
    .block-container{max-width:900px;}
    pre{background:#0b0f14;color:white;padding:12px;border-radius:8px;}
    </style>
    """,unsafe_allow_html=True)

style()

# ---------------- AUTH ----------------
if "user" not in st.session_state:
    st.session_state.user=None

if not st.session_state.user:
    st.title("Login / Register")

    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    c1,c2=st.columns(2)
    with c1:
        if st.button("Login"):
            r=cur.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone()
            if r:
                st.session_state.user=u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with c2:
        if st.button("Register"):
            cur.execute("INSERT INTO users VALUES (?,?)",(u,p))
            conn.commit()
            st.success("Registered")

    st.stop()

user=st.session_state.user

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header(f"👤 {user}")

    if st.button("Logout"):
        st.session_state.user=None
        st.rerun()

    st.divider()

    # Folders
    st.subheader("Folders")
    newf=st.text_input("New Folder")
    if st.button("Create Folder"):
        cur.execute("INSERT INTO folders VALUES (?,?,?)",
                    (str(uuid.uuid4()),user,newf))
        conn.commit()
        st.rerun()

    folders=cur.execute("SELECT id,name FROM folders WHERE user=?",(user,)).fetchall()

    for fid,fname in folders:
        with st.expander(fname):
            chats=cur.execute("SELECT id,title FROM chats WHERE folder_id=?",(fid,)).fetchall()
            for cid,title in chats:
                if st.button(title,key=cid):
                    st.session_state.chat_id=cid
                    st.rerun()

            if st.button("➕ New Chat",key=fid):
                cid=str(uuid.uuid4())
                cur.execute("INSERT INTO chats VALUES (?,?,?,?,?)",
                            (cid,user,fid,"New Chat",datetime.utcnow()))
                conn.commit()
                st.session_state.chat_id=cid
                st.rerun()

# ---------------- CHAT ----------------
if "chat_id" not in st.session_state:
    st.session_state.chat_id=None

if not st.session_state.chat_id:
    st.info("Select or create a chat")
    st.stop()

history=cur.execute(
    "SELECT role,content FROM messages WHERE chat_id=? ORDER BY created",
    (st.session_state.chat_id,)
).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- IMAGE ----------------
img_file=st.file_uploader("🖼 Upload Image",type=["png","jpg","jpeg"])

def encode_image(img):
    return base64.b64encode(img.getvalue()).decode()

# ---------------- WEB SEARCH ----------------
def web_search(q):
    url="https://duckduckgo.com/html/?q="+q
    res=requests.get(url)
    return res.text[:3000]

# ---------------- INPUT ----------------
if prompt:=st.chat_input("Ask anything..."):

    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()),st.session_state.chat_id,"user",prompt,datetime.utcnow()))
    conn.commit()

    messages=[{"role":"system","content":"You are a helpful assistant."}]

    if img_file:
        messages.append({
          "role":"user",
          "content":[
            {"type":"text","text":prompt},
            {"type":"image_url",
             "image_url":{"url":"data:image/png;base64,"+encode_image(img_file)}}
          ]
        })

    elif prompt.lower().startswith("search web"):
        data=web_search(prompt)
        messages.append({"role":"system","content":"Web data:"+data})
        messages.append({"role":"user","content":prompt})

    else:
        messages.append({"role":"user","content":prompt})

    with st.chat_message("assistant"):
        box=st.empty()
        out=""

        stream=client.chat.completions.create(
            model="llama-3.2-11b-vision-preview" if img_file else "llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )

        for ch in stream:
            if ch.choices[0].delta.content:
                out+=ch.choices[0].delta.content
                box.markdown(out)

    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()),st.session_state.chat_id,"assistant",out,datetime.utcnow()))
    conn.commit()
