import streamlit as st
import requests

from frontend.utils.ui_init import API_BASE_URL


def render_right_pane():
    """Renders the chat input area where the user can type questions about the selected PDF.
    Sends the query to the /ask endpoint and displays the response."""

    st.header("Ask Your Study Bud")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Bud:** {msg['content']}")

    st.divider()

    col_input, col_button = st.columns([4, 1], vertical_alignment="bottom")

    with col_input:
        user_query = st.text_area(
            "Ask a question about the PDF:",
            placeholder="Type your message...",
            key="user_query",
        )

    with col_button:
        send_clicked = st.button(
            "Send", use_container_width=True, type="primary"
        )

    if send_clicked:
        if user_query:
            doc_name = st.session_state.get("active_doc")
            with st.spinner("Thinking..."):
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/ask",
                        json={
                            "query": user_query,
                            "doc_name": doc_name,
                            "history": st.session_state.chat_history,
                        },
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    st.session_state.chat_history.append({"role": "user", "content": user_query})
                    st.session_state.chat_history.append({"role": "assistant", "content": data["results"]})

                    st.rerun()
                except requests.ConnectionError:
                    st.error("Could not connect to the backend. Is it running?")
                except requests.HTTPError as e:
                    st.error(f"Backend error: {e.response.text}")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
        else:
            st.warning("Please enter a question first.")