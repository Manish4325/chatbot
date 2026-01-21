import streamlit as st
from groq import Groq

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Groq Chatbot",
    page_icon="💬",
    layout="centered"
)

st.title("💬 Chatbot")
st.caption("Powered by Groq (LLaMA-3)")

# ---------------- Load API Key ----------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY not found in Streamlit Secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- Display Messages ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- Chat Input ----------------
if prompt := st.chat_input("Ask anything..."):
    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # 🔒 Limit history to avoid free-tier errors
        limited_messages = st.session_state.messages[-6:]

        response = client.chat.completions.create(
            model="llama3-8b-8192",  # safest free-tier model
            messages=limited_messages,
            temperature=0.7,
            max_tokens=512
        )

        reply = response.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })

    except Exception as e:
        # Show real error (VERY IMPORTANT)
        st.error(f"❌ Groq API error:\n\n{e}")
