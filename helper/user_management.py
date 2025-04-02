import hmac
import pandas as pd
import streamlit as st
from streamlit_server_state import no_rerun, server_state, server_state_lock


def check_password():
    """Check if a user entered the password correctly"""
    st.title(st.session_state["app_title"])

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # show input for user name
    st.session_state["user_name"] = st.selectbox(
        "User",
        st.session_state["users_list"],
        index=None,
        placeholder="Select user...",
    )

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Password incorrect")

    return False


def setup_local_files():
    """Load various settings"""
    if "users_info" not in st.session_state:
        st.session_state["users_info"] = pd.read_csv("metadata/user_list.csv")

    if "users_list" not in st.session_state:
        st.session_state["users_list"] = list(st.session_state["users_info"]["user"])

    if "settings" not in st.session_state:
        st.session_state["settings"] = pd.read_csv("metadata/settings.csv")

    if "app_title" not in st.session_state:
        st.session_state["app_title"] = (
            st.session_state["settings"]
            .loc[lambda x: x["field"] == "app_title", "value"]
            .values[0]
        )

    if "max_tokens" not in st.session_state:
        st.session_state["max_tokens"] = int(
            st.session_state["settings"]
            .loc[lambda x: x["field"] == "max_tokens", "value"]
            .values[0]
        )


def update_server_state(key, value):
    "update the server state variable"
    with no_rerun:
        with server_state_lock[key]:
            server_state[key] = value


def lock_llm():
    with no_rerun:
        with server_state_lock["llm_generating"]:
            server_state["llm_generating"] = True
        print("Locked LLM")


def unlock_llm():
    with no_rerun:
        with server_state_lock["llm_generating"]:
            server_state["llm_generating"] = False
        print("Unlocked LLM")


def unlock_llm_release_queue():
    unlock_llm()
    if server_state["exec_queue"][0] == st.session_state["user_name"]:
        update_server_state("exec_queue", server_state["exec_queue"][1:])
