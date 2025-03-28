import streamlit as st

from helper.user_management import check_password, setup_local_files
from helper.ui import (
    import_chat,
    import_styles,
    initial_placeholder,
    populate_chat,
    ui_title_icon,
    user_specific_load,
)

# load user list and llm list
setup_local_files()
ui_title_icon()

# login screen
if not check_password():
    st.stop()


### initial setup

# styles sheets
import_styles()

# placeholder on initial load
initial_placeholder()

# user specific data load
user_specific_load()


### chat logic
import_chat()
