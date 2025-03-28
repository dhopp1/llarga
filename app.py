import streamlit as st

from helper.user_management import check_password, setup_local_files
from helper.ui import ui_title_icon

# load user list and llm list
setup_local_files()
ui_title_icon()

# login screen
if not check_password():
    st.stop()
