import streamlit as st


def render_right_pane():
    """Renders the chat input area where the user can type questions about the selected PDF.
    Displays the submitted question (full API call to be added)."""
    
    st.header("💬Ask Your Study Bud ")

    # Push content down to fill space if needed
    st.container(height=500)

    col_input, col_button = st.columns([4, 1], vertical_alignment="bottom")

    with col_input:
        user_query = st.text_input(
            "Ask a question about the PDF:",
            placeholder="Type your message...",
            key="user_query",
        )

    with col_button:
        send_clicked = st.button(
            "Send", use_container_width=True, type="primary"
        )

    if send_clicked or user_query:
        if user_query:
            st.write(f"**You asked:** {user_query}")
            # Add your API call here
        else:
            st.warning("Please enter a question first.")