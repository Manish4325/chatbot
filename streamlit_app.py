import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Chatbot", page_icon="💬")

st.title("💬 Chatbot")
st.caption("Powered by OpenAI")

# Load API key from Streamlit Secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OpenAI API key not found. Add it in Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask something..."):
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Convert messages to Responses API format
    input_messages = [
        {
            "role": m["role"],
            "content": [{"type": "text", "text": m["content"]}]
        }
        for m in st.session_state.messages
    ]

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=input_messages
        )

        reply = response.output_text

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )

    except Exception as e:
        st.error("❌ Authentication failed. Check API key & billing.")
