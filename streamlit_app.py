# =========================================================
# CHATGPT-LIKE GROQ + STREAMLIT (ULTIMATE FINAL BUILD)
# =========================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid, io
from datetime import datetime
from PyPDF2 import PdfReader

# Optional voice
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except:
    VOICE_AVAILABLE = False

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
user TEXT,
title TEXT,
summary TEXT,
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
def apply_style(dark=False):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text};}}
    .block-container{{max-width:900px;padding-top:1.5rem}}
    .stChatMessage{{background:{chat};padding:14px;border-radius:12px;margin-bottom:10px}}
    pre{{background:{code}!important;color:{text}!important;padding:14px;border-radius:10px}}
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
st.session_state.setdefault("dark",False)
st.session_state.setdefault("answer_mode","Auto")

apply_style(st.session_state.dark)

# ---------------- INTENT ----------------
def detect_intent(p):
    p=p.lower()
    if any(x in p for x in ["code","program","implement","python","sql"]):
        if any(x in p for x in ["explain","what","how"]):
            return "BOTH"
        return "CODE"
    return "EXPLAIN"

def system_prompt(intent):
    if intent=="EXPLAIN":
        return "Explain clearly. Do NOT include code."
    if intent=="CODE":
        return "Return ONLY code. No explanation."
    return "Explain briefly then give one code block."

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.subheader("💬 Chats")

    chats=cur.execute("""
    SELECT id,title,pinned FROM chats
    WHERE user=? ORDER BY pinned DESC,created DESC
    """,(user,)).fetchall()

    for cid,title,pin in chats:
        label=("⭐ "+title) if pin else title
        if st.button(label,key=cid):
            st.session_state.chat_id=cid
            st.rerun()

    if st.button("➕ New Chat"):
        cid=str(uuid.uuid4())
        cur.execute("""
        INSERT INTO chats VALUES (?,?,?,?,?,?)
        """,(cid,user,"New Chat","",0,datetime.utcnow().isoformat()))
        conn.commit()
        st.session_state.chat_id=cid
        st.rerun()

    if st.session_state.chat_id:
        if st.button("⭐ Pin / Unpin"):
            cur.execute("UPDATE chats SET pinned=1-pinned WHERE id=?",
                        (st.session_state.chat_id,))
            conn.commit()
            st.rerun()

        if st.button("🗑 Delete"):
            cur.execute("DELETE FROM chats WHERE id=?",(st.session_state.chat_id,))
            cur.execute("DELETE FROM messages WHERE chat_id=?",(st.session_state.chat_id,))
            conn.commit()
            st.session_state.chat_id=None
            st.rerun()

    st.divider()
    st.session_state.answer_mode=st.selectbox(
        "Answer Mode",
        ["Auto","Explain Only","Code Only","Explain + Code"]
    )
    st.session_state.dark=st.toggle("🌙 Dark Mode",st.session_state.dark)

# ---------------- CHAT ----------------
if not st.session_state.chat_id:
    st.info("Create or select a chat")
    st.stop()

history=cur.execute("""
SELECT role,content FROM messages
WHERE chat_id=? ORDER BY created
""",(st.session_state.chat_id,)).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- FILE UPLOAD ----------------
uploads=st.file_uploader(
    "➕ Attach files",
    accept_multiple_files=True
)

context=""
if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            for p in PdfReader(f).pages:
                context+=p.extract_text() or ""
        else:
            context+=f.getvalue().decode(errors="ignore")

# ---------------- VOICE INPUT (UPLOAD AUDIO) ----------------
voice_text=""

audio_file = st.file_uploader(
    "🎤 Upload Voice (wav/mp3)",
    type=["wav","mp3"]
)

if audio_file and VOICE_AVAILABLE:
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = r.record(source)
    try:
        voice_text = r.recognize_google(audio_data)
        st.success(f"You said: {voice_text}")
    except:
        st.error("Could not understand audio")

# ---------------- INPUT ----------------
prompt=st.chat_input("Ask anything...")

if voice_text and not prompt:
    prompt=voice_text

if prompt:

    cur.execute("""
    INSERT INTO messages VALUES (?,?,?,?,?)
    """,(str(uuid.uuid4()),st.session_state.chat_id,
         "user",prompt,datetime.utcnow().isoformat()))
    conn.commit()

    row=cur.execute("SELECT title FROM chats WHERE id=?",
                    (st.session_state.chat_id,)).fetchone()

    if row and row[0]=="New Chat":
        title=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"user","content":f"Give short title: {prompt}"}]
        ).choices[0].message.content[:40]

        cur.execute("UPDATE chats SET title=? WHERE id=?",
                    (title,st.session_state.chat_id))
        conn.commit()

    if st.session_state.answer_mode=="Auto":
        intent=detect_intent(prompt)
    elif st.session_state.answer_mode=="Explain Only":
        intent="EXPLAIN"
    elif st.session_state.answer_mode=="Code Only":
        intent="CODE"
    else:
        intent="BOTH"

    messages=[{"role":"system","content":system_prompt(intent)}]

    if context:
        messages.append({"role":"system","content":"Context:\n"+context})

    recent=cur.execute("""
    SELECT role,content FROM messages
    WHERE chat_id=? ORDER BY created DESC LIMIT 6
    """,(st.session_state.chat_id,)).fetchall()

    messages.extend(reversed([{"role":r,"content":c} for r,c in recent]))

    with st.chat_message("assistant"):
        box=st.empty()
        out=""
        stream=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                out+=chunk.choices[0].delta.content
                box.markdown(out+"<span class='typing'></span>",
                             unsafe_allow_html=True)

    cur.execute("""
    INSERT INTO messages VALUES (?,?,?,?,?)
    """,(str(uuid.uuid4()),st.session_state.chat_id,
         "assistant",out,datetime.utcnow().isoformat()))
    conn.commit()

# ---------------- EXPORT CHAT ----------------
st.divider()
if st.button("📤 Export Chat"):
    rows=cur.execute("""
    SELECT role,content FROM messages
    WHERE chat_id=? ORDER BY created
    """,(st.session_state.chat_id,)).fetchall()

    text=""
    for r,c in rows:
        text+=f"{r.upper()}:\n{c}\n\n"

    st.download_button(
        "Download TXT",
        text,
        file_name="chat.txt"
    )

# =========================================================
# DEPLOYMENT
# Streamlit Cloud:
# - Push to GitHub
# - Add GROQ_API_KEY in Secrets
#
# Render:
# Start Command:
# streamlit run streamlit_app.py --server.port 10000 --server.address 0.0.0.0
# =========================================================
