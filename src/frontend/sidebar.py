import streamlit as st
import requests
from frontend.utils.ui_init import API_BASE_URL

def fetch_file_list():
    """Calls the backend API and returns a list of uploaded PDF filenames.
    Shows a sidebar error and returns an empty list if the request fails."""

    try:
        response = requests.get(f"{API_BASE_URL}/list_files", timeout=5)
        if response.status_code == 200:
            # Expecting JSON like: {"files": ["doc1.pdf", "doc2.pdf"]}
            return response.json().get("files", [])
        else:
            st.sidebar.error(
                f"Failed to fetch files (Status {response.status_code})"
            )
            return []
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Could not connect to API: {e}")
        return []

def upload_file(file):
    """Posts the given file to the backend upload endpoint and returns True on 
    success."""

    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
        return response.status_code in (200, 201)
    except requests.exceptions.RequestException:
        return False

        


def render_sidebar():
    """Renders the sidebar with a PDF uploader and document selector.
    Returns the filename of the currently selected document, or None if none is selected."""

    
    st.sidebar.title("Study Bud")
    st.sidebar.text("📥Upload PDF files...")

    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file is not None:

        with st.sidebar.spinner("Uploading..."):
            if upload_file(uploaded_file):
                st.sidebar.success("File uploaded successfully!")
                st.rerun()
            else:
                st.sidebar.error("Failed to upload file.")

    
    st.sidebar.divider()

    # --- Section 2: Dynamic Document Selection ---
    st.sidebar.subheader("🗃️Uploaded Documents")

    file_list = fetch_file_list()

    selected_document = None

    if file_list:
        selected_document = st.sidebar.selectbox(
            "Select active document:",
            options=file_list,
            key="active_pdf_selection",
        )
        st.sidebar.caption(f"🎯 Selected: **{selected_document}**")
    else:
        st.sidebar.info("🚫 No documents found.")

    # Optional Manual Refresh Button
    if st.sidebar.button("🔄"):
        st.rerun()

    return selected_document
