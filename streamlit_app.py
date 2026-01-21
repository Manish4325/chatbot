import streamlit as st
from groq import Groq

# Page config
st.set_page_config(
    page_title="Groq Chatbot",
    page_icon="💬",
    layout="centered"
)

st.title("💬 Chatbot")
st.caption("Powered by Groq (LLaMA-3)")

# Load Groq API key from Streamlit Secrets
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY not found. Add it in Streamlit Secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask anything..."):
    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Call Groq API
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # FREE + FAST
            messages=st.session_state.messages
        )

        assistant_reply = response.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(assistant_reply)

        # Save assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

    except Exception as e:
        st.error("❌ Groq API error. Try again later.")
