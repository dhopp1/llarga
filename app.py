import streamlit as st
from streamlit_server_state import server_state

from helper.sidebar import (
    sidebar_chats,
    sidebar_delete_corpus,
    sidebar_export_chat,
    gen_export_df,
    sidebar_llm_api_key,
    sidebar_llm_dropdown,
    sidebar_temperature_dropdown,
    sidebar_system_prompt,
    sidebar_upload_file,
    sidebar_which_corpus,
)
from helper.user_management import check_password, setup_local_files
from helper.ui import (
    import_chat,
    import_styles,
    initial_placeholder,
    metadata_tab,
    save_user_settings,
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
# previous chats
st.sidebar.markdown("### Chats")
sidebar_chats()

# corpus info
st.sidebar.markdown("### Corpus")
with st.sidebar:
    sidebar_which_corpus()
    gen_export_df()
    with st.expander("Corpus metadata"):
        metadata_tab()

with st.sidebar.expander("Upload your own documents"):
    st.markdown("#### Upload a new corpus")
    sidebar_upload_file()
    st.markdown("#### Delete a corpus")
    sidebar_delete_corpus()

# llm info
st.sidebar.markdown("### LLM")
with st.sidebar.expander("LLM parameters"):
    sidebar_llm_dropdown()
    sidebar_llm_api_key()
    sidebar_temperature_dropdown()
    sidebar_system_prompt()

# warning if system prompt is different different
with st.sidebar:
    if (
        st.session_state["default_system_prompt"]
        != server_state[f"{st.session_state['user_name']}_system_prompt"]
    ):
        st.warning(
            "The default system prompt for this corpus differs from what you have input in `System prompt` under the `LLM parameters` dropdown. Consider changing it."
        )


# user specific data load
user_specific_load()


### chat logic
import_chat()


# export chat button
with st.sidebar:
    sidebar_export_chat()
