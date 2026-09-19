import streamlit as st 
from frontend.sidebar import render_sidebar
from frontend.leftpanel import render_left_pane
from frontend.rightpanel import render_right_pane



# Expand app layout to full width
st.set_page_config(page_title="Study Bud", layout="wide")

# 1. Render Sidebar & retrieve uploaded file
selected_filename = render_sidebar()

# 2. Split main area into 2 equal columns
col_left, col_right = st.columns([2, 1], gap="large")

# 3. Render left pane (PDF) & right pane (Chat/Input)
with col_left:
    render_left_pane(selected_filename)

with col_right:
    render_right_pane()