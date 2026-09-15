import streamlit as st

def render_sidebar():
    st.sidebar.title("Study Bud")
    st.sidebar.text("📥Upload PDF files...")

    file = st.sidebar.file_uploader("Upload PDFs files Only", type=["pdf"])

    if file is not None:
        st.sidebar.write(f"**Filename:** {file.name}")
        st.sidebar.write(f"**Size:** {file.size} bytes")
    else:
        st.sidebar.info("No file Uploaded")
        return None

    return file