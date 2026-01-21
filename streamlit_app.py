import streamlit as st
from groq import Groq

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Groq Chatbot",
    page_icon="💬",
    layout="centered"
)

st.title("💬 Chatbot")
st.caption("Powered by Groq (LLaMA-3.1)")

# ---------------- API Key ----------------
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
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Limit history (free-tier safe)
        context = st.session_state.messages[-6:]

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            # 🔥 STREAMING RESPONSE
            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=context,
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

    except Exception as e:
        st.error(f"❌ Groq API error:\n\n{e}")
