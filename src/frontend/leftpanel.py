import base64
import requests
import streamlit as st
from .utils.ui_init import API_BASE_URL


def render_left_pane(selected_filename):
    """Fetches the selected PDF from the backend and displays it in an embedded iframe.
    Shows a placeholder message if no document has been selected yet."""

    st.header("📃File Preview")

    if not selected_filename:
        st.info("👈 Select or upload a document from the sidebar to view it.")
        return

    if isinstance(selected_filename, str):
        try:
            response = requests.get(
                f"{API_BASE_URL}/files/{selected_filename}"
            )
            if response.status_code == 200:
                pdf_bytes = response.content
            else:
                st.error("Failed to retrieve document from server.")
                return
        except requests.exceptions.RequestException:
            st.error("Could not connect to backend server.")
            return

    else:
        # If passed an UploadedFile object directly
        pdf_bytes = selected_filename.getvalue()

    # Encode raw bytes to base64 and render via st.iframe
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_src = f"data:application/pdf;base64,{base64_pdf}"

    st.iframe(src=pdf_src, height=700)

    