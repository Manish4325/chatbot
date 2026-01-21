import streamlit as st
from openai import OpenAI

# Page config
st.set_page_config(page_title="Chatbot", page_icon="💬")

st.title("💬 Chatbot")
st.write("A simple Streamlit chatbot using OpenAI Responses API")

# API Key input
openai_api_key = st.text_input("OpenAI API Key", type="password")

if not openai_api_key:
    st.info("Please enter your OpenAI API key to continue 🔑")
    st.stop()

# Create OpenAI client
client = OpenAI(api_key=openai_api_key)

# Session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Ask something..."):

    # Store user message
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare conversation for API
    conversation = []
    for m in st.session_state.messages:
        conversation.append({
            "role": m["role"],
            "content": [{"type": "text", "text": m["content"]}]
        })

    # Call OpenAI Responses API
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=conversation
    )

    assistant_reply = response.output_text

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(assistant_reply)

    # Save assistant response
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_reply}
    )
