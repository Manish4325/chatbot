# =========================================================
# CHATGPT-LIKE GROQ + STREAMLIT (ULTIMATE EDITION)
# =========================================================

import streamlit as st
from groq import Groq
import sqlite3, uuid, time, re
from datetime import datetime
from PyPDF2 import PdfReader

# ================= CONFIG =================
st.set_page_config("Chatbot", "💬", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("chat.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS chats(
id TEXT PRIMARY KEY,
user TEXT,
title TEXT,
summary TEXT,
pinned INTEGER,
created TEXT)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
id TEXT,
chat_id TEXT,
role TEXT,
content TEXT,
created TEXT)
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_id ON messages(chat_id)")
conn.commit()

# ================= GROQ =================
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ================= STYLE =================
def style(dark):
    bg="#0f1117" if dark else "#ffffff"
    chat="#1e1f24" if dark else "#f7f7f8"
    text="#eaeaea" if dark else "#1f1f1f"
    code="#0b0f14" if dark else "#f1f1f1"

    st.markdown(f"""
<style>
body,.stApp{{background:{bg};color:{text};}}
.block-container{{max-width:900px;padding-top:1rem}}
.stChatMessage{{background:{chat};padding:14px;border-radius:12px;margin-bottom:10px}}
pre{{background:{code}!important;color:{text}!important;padding:14px;border-radius:10px}}
.typing::after{{content:"▍";animation:blink 1s infinite}}
@keyframes blink{{50%{{opacity:0}}}}
</style>
""",unsafe_allow_html=True)

# ================= LOGIN =================
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

# ================= STATE =================
st.session_state.setdefault("chat_id",None)
st.session_state.setdefault("dark",False)
st.session_state.setdefault("answer_mode","Auto")
st.session_state.setdefault("max_tokens",600)
style(st.session_state.dark)

# ================= RATE LIMIT =================
if "last_msg" not in st.session_state:
    st.session_state.last_msg=0

def rate_limited():
    return time.time()-st.session_state.last_msg<2

# ================= INTENT =================
def detect_intent(p):
    p=p.lower()
    if "only code" in p: return "CODE"
    if "only explain" in p: return "EXPLAIN"
    code=["code","program","implement","python","java","sql"]
    explain=["explain","what is","define","why","how"]
    if any(c in p for c in code) and any(e in p for e in explain): return "BOTH"
    if any(c in p for c in code): return "CODE"
    return "EXPLAIN"

def system_prompt(intent):
    base="""
Reply in the same language as the user.
If unsure, say I don't know.
Assume short questions are follow-ups.
"""
    if intent=="EXPLAIN":
        return base+"Explain clearly. No code."
    if intent=="CODE":
        return base+"Only code. No explanation."
    return base+"Explain briefly then give one code block."

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("💬 Chats")
    search=st.text_input("Search")

    rows=cur.execute("""
    SELECT id,title,pinned FROM chats
    WHERE user=? AND title LIKE ?
    ORDER BY pinned DESC,created DESC
    """,(user,f"%{search}%")).fetchall()

    for cid,title,pinned in rows:
        label=f"⭐ {title}" if pinned else title
        if st.button(label,key=cid):
            st.session_state.chat_id=cid
            st.rerun()

    if st.button("➕ New Chat"):
        cid=str(uuid.uuid4())
        cur.execute("INSERT INTO chats VALUES (?,?,?,?,?)",
        (cid,user,"New Chat","",0,datetime.utcnow().isoformat()))
        conn.commit()
        st.session_state.chat_id=cid
        st.rerun()

    if st.session_state.chat_id:
        if st.button("⭐ Pin"):
            cur.execute("UPDATE chats SET pinned=1-pinned WHERE id=?",
            (st.session_state.chat_id,))
            conn.commit()
            st.rerun()

        new_name=st.text_input("Rename Chat")
        if new_name:
            cur.execute("UPDATE chats SET title=? WHERE id=?",
            (new_name,st.session_state.chat_id))
            conn.commit()

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
    st.session_state.max_tokens=st.slider("Response length",200,2000,600)
    st.session_state.dark=st.toggle("🌙 Dark",st.session_state.dark)

# ================= CHAT =================
if not st.session_state.chat_id:
    st.info("Create or select chat")
    st.stop()

msgs=cur.execute("""
SELECT role,content FROM messages
WHERE chat_id=? ORDER BY created
""",(st.session_state.chat_id,)).fetchall()

for r,c in msgs:
    with st.chat_message(r):
        st.markdown(c)
        if r=="assistant":
            st.button("📋 Copy",key=str(uuid.uuid4()),
                      on_click=lambda t=c: st.session_state.update({"_copy":t}))

# ================= FILE ATTACH =================
with st.expander("➕ Attach",False):
    uploads=st.file_uploader(
        "Files",
        ["pdf","txt","py","html","ipynb","png","jpg"],
        accept_multiple_files=True
    )

context=""
if uploads:
    for f in uploads:
        if f.type=="application/pdf":
            for p in PdfReader(f).pages:
                context+=p.extract_text() or ""
        elif f.type.startswith("image"):
            context+="\n[Image uploaded]"
        else:
            context+=f.getvalue().decode(errors="ignore")

# ================= INPUT =================
if prompt:=st.chat_input("Ask anything"):
    if rate_limited():
        st.warning("Slow down...")
        st.stop()

    st.session_state.last_msg=time.time()

    cur.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
    (str(uuid.uuid4()),st.session_state.chat_id,
     "user",prompt,datetime.utcnow().isoformat()))
    conn.commit()

    row=cur.execute("SELECT title,summary FROM chats WHERE id=?",
    (st.session_state.chat_id,)).fetchone()
    title=row[0]
    summary=row[1] or ""

    if title=="New Chat":
        auto=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"user","content":f"Give short title: {prompt}"}]
        ).choices[0].message.content[:40]
        cur.execute("UPDATE chats SET title=? WHERE id=?",
        (auto,st.session_state.chat_id))
        conn.commit()

    if st.session_state.answer_mode=="Auto":
        intent=detect_intent(prompt)
    elif st.session_state.answer_mode=="Explain Only":
        intent="EXPLAIN"
    elif st.session_state.answer_mode=="Code Only":
        intent="CODE"
    else:
        intent="BOTH"

    sys=system_prompt(intent)

    history=cur.execute("""
    SELECT role,content FROM messages
    WHERE chat_id=? ORDER BY created DESC LIMIT 6
    """,(st.session_state.chat_id,)).fetchall()

    messages=[{"role":"system","content":sys}]
    if summary:
        messages.append({"role":"system","content":"Conversation summary:"+summary})
    if context:
        messages.append({"role":"system","content":"Context:"+context})

    messages.extend(reversed([{"role":r,"content":c} for r,c in history]))

    with st.chat_message("assistant"):
        box=st.empty()
        out=""
        try:
            stream=client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=st.session_state.max_tokens,
                stream=True
            )
            for ch in stream:
                if ch.choices[0].delta.content:
                    out+=ch.choices[0].delta.content
                    box.markdown(out+"<span class='typing'></span>",unsafe_allow_html=True)
        except:
            st.error("Model temporarily unavailable")

    cur.execute(
    "INSERT INTO chats VALUES (?,?,?,?,?,?)",
    (cid, user, "New Chat", "", 0, datetime.utcnow().isoformat())
)
conn.commit()


    # ===== SUMMARY UPDATE =====
    all_text="\n".join([m[1] for m in history[::-1]])
    if len(all_text)>3000:
        s=client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"user","content":"Summarize briefly:"+all_text}]
        ).choices[0].message.content
        cur.execute("UPDATE chats SET summary=? WHERE id=?",
        (s,st.session_state.chat_id))
        conn.commit()
