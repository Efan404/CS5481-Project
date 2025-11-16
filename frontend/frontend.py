import json

import requests
import streamlit as st

headers = {
  'Content-Type': 'application/json'
}

system_prompt = "You are a medical assistant caring for users who cannot afford hospital.\nIn each query, you will be given three relevant knowledge chuncks from professional medical textbooks.\nIf the retrieved chunks are irrelevant to the question, don't provide any information other than generic greetings.\nIf the retrieved knowledge is relevant, address their signs and concerns with professional knowledge in a friendly approach."

RAG_URL = "http://localhost:8964/api/rag"
CHAT_URL = "http://localhost:8964/api/chat"

# Set up page configuration
st.set_page_config(page_title="Ollama Streamlit Chat", layout="centered")
st.title("MedBot - Simple and Free Medical Q&A")

with st.expander("Disclaimer"):
    st.write('''
        This medical Q&A system is for informational purposes only and should not be considered a substitute for professional medical advice, diagnosis, or treatment.
    ''')

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        intermediate = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        intermediate.insert(0, {"role": "system", "content": system_prompt})
        
        payload = json.dumps(intermediate[-1]["content"])
        try:
            response = requests.post(RAG_URL, headers=headers, data=payload, timeout=60)
            response.raise_for_status()
            augmented_query = response.text
        except requests.RequestException as exc:
            message_placeholder.error(f"Context retrieval failed: {exc}")
            augmented_query = intermediate[-1]["content"]

        intermediate[-1]["content"] = augmented_query

        chat_request = {
            "model": "deepseek/deepseek-v3.2-exp",
            "messages": intermediate,
            "stream": False,
        }

        try:
            chat_response = requests.post(CHAT_URL, json=chat_request, timeout=120)
            chat_response.raise_for_status()
            chat_json = chat_response.json()
            choices = chat_json.get("choices", [])
            if choices:
                full_response = choices[0].get("message", {}).get("content", "")
            else:
                full_response = chat_json.get("content", "") or chat_json.get("error", {}).get("message", "") or "No response received."
            message_placeholder.markdown(full_response)
        except requests.RequestException as exc:
            full_response = ""
            message_placeholder.error(f"LLM request failed: {exc}")


    st.session_state.messages.append({"role": "assistant", "content": full_response})
