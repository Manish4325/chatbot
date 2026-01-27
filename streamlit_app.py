# =========================================================
# CHATGPT STYLE STREAMLIT + GROQ (PRODUCTION READY)
# =========================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid
from datetime import datetime
from PyPDF2 import PdfReader

# ---------------- PAGE ----------------
st.set_page_config("Chatbot", "💬", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

# FOLDERS
cur.execute("""
CREATE TABLE IF NOT EXISTS folders(
id TEXT,
user TEXT,
name TEXT
)
""")

# CHATS
cur.execute("""
CREATE TABLE IF NOT EXISTS chats(
id TEXT,
user TEXT,
title TEXT,
pinned INTEGER,
created TEXT,
folder_id TEXT
)
""")

# MESSAGES
cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
id TEXT,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT
)
""")

# ---- AUTO MIGRATION (SAFE) ----
try:
    cur.execute("ALTER TABLE chats ADD COLUMN folder_id TEXT")
except:
    pass   # column already exists

conn.commit()

# ---------------- GROQ ----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- STYLE ----------------
def apply_style(dark=False):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text}}}
    .block-container{{max-width:900px}}
    .stChatMessage{{background:{chat};border-radius:12px;padding:14px;margin-bottom:10px}}
    pre{{background:{code}!important;color:{text}!important;border-radius:10px;padding:12px}}
    .typing::after{{content:"▍";animation:blink 1s infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    @media(max-width:768px){{.block-container{{padding:1rem}}}}
    </style>
    """, unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    name = st.text_input("Enter your name")
    if st.button("Start") and name:
        st.session_state.user = name
        st.rerun()
    st.stop()

user = st.session_state.user

# ---------------- STATE ----------------
st.session_state.setdefault("chat_id", None)
st.session_state.setdefault("dark", False)
st.session_state.setdefault("answer_mode", "Auto")

apply_style(st.session_state.dark)

# ---------------- INTENT ----------------
def detect_intent(p):
    p=p.lower()
    if any(x in p for x in ["code","program","script","python","sql"]):
        return "CODE"
    if any(x in p for x in ["explain","what is","define","why"]):
        return "EXPLAIN"
    return "BOTH"

def system_prompt(i):
    if i=="CODE":
        return "Return ONLY code. No explanation."
    if i=="EXPLAIN":
        return "Explain clearly. Do not include code."
    return "Explain briefly then provide code."

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header(user)

    # GLOBAL NEW CHAT
    if st.button("➕ New Chat"):
        row = cur.execute(
            "SELECT id FROM folders WHERE user=? LIMIT 1",(user,)
        ).fetchone()

        if not row:
            fid=str(uuid.uuid4())
            cur.execute("INSERT INTO folders VALUES(?,?,?)",
                        (fid,user,"Default"))
        else:
            fid=row[0]

        cid=str(uuid.uuid4())
        cur.execute("""INSERT INTO chats VALUES(?,?,?,?,?,?)""",
                    (cid,user,"New Chat",0,
                     datetime.utcnow().isoformat(),fid))
        conn.commit()
        st.session_state.chat_id=cid
        st.rerun()

    st.session_state.dark = st.toggle("🌙 Dark Mode", st.session_state.dark)
    st.session_state.answer_mode = st.selectbox(
        "Answer Mode",
        ["Auto","Explain Only","Code Only","Explain + Code"]
    )

    st.divider()

    # CREATE FOLDER
    fname=st.text_input("New Folder")
    if st.button("Create Folder"):
        cur.execute("INSERT INTO folders VALUES(?,?,?)",
                    (str(uuid.uuid4()),user,fname))
        conn.commit()
        st.rerun()

    folders=cur.execute(
        "SELECT id,name FROM folders WHERE user=?",(user,)
    ).fetchall()

    for fid,name in folders:
        with st.expander(name):
            chats=cur.execute("""
            SELECT id,title FROM chats
            WHERE folder_id=? ORDER BY created DESC
            """,(fid,)).fetchall()

            for cid,title in chats:
                if st.button(title,key=cid):
                    st.session_state.chat_id=cid
                    st.rerun()

# ---------------- NO CHAT ----------------
if not st.session_state.chat_id:
    st.info("Select or create a chat")
    st.stop()

# ---------------- HISTORY ----------------
history=cur.execute("""
SELECT role,content FROM messages
WHERE chat_id=? ORDER BY created
""",(st.session_state.chat_id,)).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- FILE UPLOAD ----------------
with st.expander("➕ Attach files"):
    uploads=st.file_uploader(
        "Upload",
        type=["pdf","txt","csv","py","html","ipynb","png","jpg"],
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
            context+="\n[Image uploaded]"
        else:
            context+=f.getvalue().decode(errors="ignore")

# ---------------- INPUT ----------------
if prompt:=st.chat_input("Ask anything..."):
    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()),
                 st.session_state.chat_id,
                 "user",prompt,
                 datetime.utcnow().isoformat()))
    conn.commit()

    mode=st.session_state.answer_mode
    if mode=="Auto":
        intent=detect_intent(prompt)
    elif mode=="Explain Only":
        intent="EXPLAIN"
    elif mode=="Code Only":
        intent="CODE"
    else:
        intent="BOTH"

    messages=[{"role":"system",
               "content":system_prompt(intent)}]

    if context:
        messages.append({"role":"system",
                         "content":f"Context:\n{context}"})

    recent=cur.execute("""
    SELECT role,content FROM messages
    WHERE chat_id=? ORDER BY created DESC LIMIT 6
    """,(st.session_state.chat_id,)).fetchall()

    messages.extend(reversed(
        [{"role":r,"content":c} for r,c in recent]
    ))

    with st.chat_message("assistant"):
        box=st.empty()
        out=""
        stream=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )
        for ch in stream:
            if ch.choices[0].delta.content:
                out+=ch.choices[0].delta.content
                box.markdown(out+
                             '<span class="typing"></span>',
                             unsafe_allow_html=True)

    cur.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()),
                 st.session_state.chat_id,
                 "assistant",out,
                 datetime.utcnow().isoformat()))
    conn.commit()
