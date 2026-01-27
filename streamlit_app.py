# ============================================================
# CHATGPT STYLE STREAMLIT + GROQ CHATBOT (FINAL STABLE BUILD)
# ============================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid
from datetime import datetime
from PyPDF2 import PdfReader

# ---------------- CONFIG ----------------
st.set_page_config("Chatbot", "💬", layout="wide")

# ---------------- SECRETS CHECK ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing in Streamlit secrets")
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
def apply_style(dark=False):
    bg = "#0f1117" if dark else "#ffffff"
    chat = "#1e1f24" if dark else "#f7f7f8"
    text = "#eaeaea" if dark else "#1f1f1f"
    code = "#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
    <style>
    body,.stApp{{background:{bg};color:{text};}}
    .block-container{{max-width:900px;padding-top:1rem;}}

    .stChatMessage{{
        background:{chat};
        border-radius:12px;
        padding:14px;
        margin-bottom:10px;
    }}

    pre{{background:{code};padding:14px;border-radius:10px}}

    .typing::after{{
        content:"▍";
        animation:blink 1s infinite;
    }}

    @keyframes blink{{50%{{opacity:0;}}}}

    @media(max-width:768px){{
        .block-container{{padding:0.5rem}}
    }}
    </style>
    """, unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("💬 Chatbot")
    name = st.text_input("Enter your name")
    if st.button("Start Chat") and name:
        st.session_state.user = name
        st.rerun()
    st.stop()

user = st.session_state.user

# ---------------- STATE ----------------
st.session_state.setdefault("chat_id", None)
st.session_state.setdefault("dark", False)
st.session_state.setdefault("mode", "Auto")

apply_style(st.session_state.dark)

# ---------------- INTENT ----------------
def detect_intent(p):
    p = p.lower()
    if any(w in p for w in ["code","program","script","python","java","sql"]):
        if any(w in p for w in ["explain","what","how"]):
            return "BOTH"
        return "CODE"
    return "EXPLAIN"

def system_prompt(intent):
    if intent=="CODE":
        return "Write ONLY code. No explanation."
    if intent=="EXPLAIN":
        return "Explain clearly. No code."
    return "Explain briefly then give code."

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.subheader("💬 Chats")

    chats = cur.execute("""
    SELECT id,title,pinned FROM chats
    WHERE user=?
    ORDER BY pinned DESC, created DESC
    """,(user,)).fetchall()

    for cid,title,pinned in chats:
        label = f"⭐ {title}" if pinned else title
        if st.button(label,key=cid):
            st.session_state.chat_id = cid
            st.rerun()

    if st.button("➕ New Chat"):
        cid = str(uuid.uuid4())
        cur.execute("""
        INSERT INTO chats VALUES(?,?,?,?,?)
        """,(cid,user,"New Chat",0,datetime.utcnow().isoformat()))
        conn.commit()
        st.session_state.chat_id = cid
        st.rerun()

    if st.session_state.chat_id:
        if st.button("⭐ Pin / Unpin"):
            cur.execute("""
            UPDATE chats SET pinned = 1 - pinned WHERE id=?
            """,(st.session_state.chat_id,))
            conn.commit()
            st.rerun()

        if st.button("🗑 Delete"):
            cur.execute("DELETE FROM chats WHERE id=?",(st.session_state.chat_id,))
            cur.execute("DELETE FROM messages WHERE chat_id=?",(st.session_state.chat_id,))
            conn.commit()
            st.session_state.chat_id=None
            st.rerun()

    st.divider()
    st.session_state.mode = st.selectbox(
        "Answer Mode",
        ["Auto","Explain Only","Code Only","Explain + Code"]
    )
    st.session_state.dark = st.toggle("🌙 Dark mode",st.session_state.dark)

# ---------------- CHAT ----------------
if not st.session_state.chat_id:
    st.info("Select or create a chat")
    st.stop()

history = cur.execute("""
SELECT role,content FROM messages
WHERE chat_id=?
ORDER BY created
""",(st.session_state.chat_id,)).fetchall()

for r,c in history:
    with st.chat_message(r):
        st.markdown(c)

# ---------------- FILE UPLOAD ----------------
uploads = st.file_uploader(
    "Attach files",
    type=["pdf","txt","csv","py","html","ipynb","png","jpg"],
    accept_multiple_files=True
)

context = ""
if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            reader = PdfReader(f)
            for p in reader.pages:
                context += p.extract_text() or ""
        else:
            context += f.getvalue().decode(errors="ignore")

# ---------------- INPUT ----------------
if prompt := st.chat_input("Ask anything..."):

    cur.execute("""
    INSERT INTO messages VALUES(?,?,?,?,?)
    """,(str(uuid.uuid4()),
        st.session_state.chat_id,
        "user",
        prompt,
        datetime.utcnow().isoformat()))
    conn.commit()

    title = cur.execute("""
    SELECT title FROM chats WHERE id=?
    """,(st.session_state.chat_id,)).fetchone()[0]

    if title=="New Chat":
        auto = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role":"user","content":f"Short title: {prompt}"}]
        ).choices[0].message.content[:40]

        cur.execute("""
        UPDATE chats SET title=? WHERE id=?
        """,(auto,st.session_state.chat_id))
        conn.commit()

    if st.session_state.mode=="Auto":
        intent = detect_intent(prompt)
    elif st.session_state.mode=="Explain Only":
        intent="EXPLAIN"
    elif st.session_state.mode=="Code Only":
        intent="CODE"
    else:
        intent="BOTH"

    messages=[{"role":"system","content":system_prompt(intent)}]

    if context:
        messages.append({"role":"system","content":f"Context:\n{context}"})

    recent = cur.execute("""
    SELECT role,content FROM messages
    WHERE chat_id=?
    ORDER BY created DESC LIMIT 6
    """,(st.session_state.chat_id,)).fetchall()

    messages.extend(reversed([{"role":r,"content":c} for r,c in recent]))

    with st.chat_message("assistant"):
        box = st.empty()
        out=""

        try:
            stream = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                stream=True
            )
        except:
            st.error("Groq API error. Check key or model.")
            st.stop()

        for ch in stream:
            if ch.choices[0].delta.content:
                out += ch.choices[0].delta.content
                box.markdown(out+'<span class="typing"></span>',unsafe_allow_html=True)

    cur.execute("""
    INSERT INTO messages VALUES(?,?,?,?,?)
    """,(str(uuid.uuid4()),
        st.session_state.chat_id,
        "assistant",
        out,
        datetime.utcnow().isoformat()))
    conn.commit()
