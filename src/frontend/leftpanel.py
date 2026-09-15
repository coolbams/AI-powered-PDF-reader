import base64
import streamlit as st
import streamlit.components.v1 as components


def render_left_pane(uploaded_file):
    st.header("📃File Preview")

    if uploaded_file is not None:

        pdf_bytes = uploaded_file.getvalue()
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        pdf_display = f"""

        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="700vh" 
            type="application/pdf"
            style="border: none; border-radius: 8px; margin:10px 20px; ">
        </iframe>

        """

        components.html(pdf_display, height=710, scrolling=False)
        # st.iframe("https://docs.streamlit.io",height=800)

    else:
        st.info("Upload a PDF from the sidebar to view it here.")