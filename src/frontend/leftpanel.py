
import requests
import streamlit as st
from .utils.ui_init import API_BASE_URL


def render_left_pane(selected_filename):
    """Fetches the selected PDF from the backend and displays it in an embedded native PDF viewer.
    Shows a placeholder message if no document has been selected yet."""

    st.header("File Preview")

    options = ["PDF file", "Markdown"]

    icon_map = {
    "PDF file": ":material/picture_as_pdf: PDF file",
    "Markdown": ":material/markdown: Markdown",
    
}

    selected = st.pills(
    " ",
    options=options,
    format_func=lambda x: icon_map[x],
    selection_mode="single"
)

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

    st.pdf(pdf_bytes, height=600)

    