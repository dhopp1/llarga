import streamlit as st

from helper.sidebar import (
    sidebar_llm_api_key,
    sidebar_llm_dropdown,
    sidebar_temperature_dropdown,
    sidebar_system_prompt,
    sidebar_which_corpus,
)
from helper.user_management import check_password, setup_local_files
from helper.ui import (
    import_chat,
    import_styles,
    initial_placeholder,
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

### sidebar
# corpus info
st.sidebar.markdown("### Corpus")
sidebar_which_corpus()

# llm info
st.sidebar.markdown("### LLM parameters")
sidebar_llm_dropdown()
sidebar_llm_api_key()
sidebar_temperature_dropdown()
sidebar_system_prompt()


# user specific data load
user_specific_load()


### chat logic
import_chat()
