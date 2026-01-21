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

# ---------------- System Prompt ----------------
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful AI assistant. "
        "Always provide COMPLETE answers. "
        "If the question is technical, ALWAYS include a full working example. "
        "Never stop mid-sentence. "
        "Use clear explanations and proper markdown formatting."
    )
}

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [SYSTEM_PROMPT]

if "last_incomplete" not in st.session_state:
    st.session_state.last_incomplete = False

# ---------------- Sidebar Controls ----------------
with st.sidebar:
    st.header("⚙️ Controls")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = [SYSTEM_PROMPT]
        st.session_state.last_incomplete = False
        st.rerun()

# ---------------- Display Messages ----------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
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

    def generate_response(extra_instruction=None):
        context = st.session_state.messages[-8:]

        if extra_instruction:
            context.append({
                "role": "user",
                "content": extra_instruction
            })

        full_response = ""
        truncated = False

        with st.chat_message("assistant"):
            placeholder = st.empty()

            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=context,
                temperature=0.6,
                max_tokens=1024,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response)

            if not full_response.strip().endswith((".", "```")):
                truncated = True

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

        st.session_state.last_incomplete = truncated

    try:
        generate_response()

    except Exception as e:
        st.error(f"❌ Groq API error:\n\n{e}")

# ---------------- Continue Button ----------------
if st.session_state.last_incomplete:
    if st.button("▶ Continue response"):
        try:
            generate_response(
                extra_instruction="Continue the previous answer from where you stopped. Complete it fully."
            )
            st.session_state.last_incomplete = False
        except Exception as e:
            st.error(f"❌ Groq API error:\n\n{e}")
