import base64
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from .utils.ui_init import API_BASE_URL


def render_left_pane(selected_filename):
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


    # Encode raw bytes to base64 and render iframe
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    pdf_display = f"""
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="680px" 
            type="application/pdf"
            style="border: 1px solid #e6e6e6; border-radius: 8px;">
        </iframe>
    """
    components.html(pdf_display, height=700, scrolling=False)

    