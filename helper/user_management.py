from datetime import datetime, timedelta
import gc
import hmac
import math
import subprocess as sp
import psutil

import pandas as pd
import streamlit as st
from streamlit_server_state import server_state, server_state_lock, no_rerun


def check_password():
    """Check if a user entered the password correctly"""
    if not (st.session_state["available"]):
        st.error("The LLM is currently generating, try again in a few seconds.")

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        st.session_state["override"] = False
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        # override password
        elif hmac.compare_digest(st.session_state["password"], st.secrets["override"]):
            st.session_state["password_correct"] = True
            st.session_state["override"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        if st.session_state["available"]:
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


def update_server_state(key, value):
    "update the server state variable"
    with no_rerun:
        with server_state_lock[key]:
            server_state[key] = value


def clear_models():
    if f'model_{st.session_state["db_name"]}' in server_state:
        try:
            server_state[f'model_{st.session_state["db_name"]}'].close_connection()
        except:
            pass
        del server_state[f'model_{st.session_state["db_name"]}']
        gc.collect()


def determine_availability():
    "determine if the application is available to the user"
    # user list
    if "users_list" not in st.session_state:
        st.session_state["users_list"] = pd.read_csv("metadata/user_list.csv")

    # if never been used, available
    if "in_use" not in server_state:
        update_server_state("in_use", False)

    # only unable to log in if the model is currently generating and the user has not booted in already
    if "first_boot" not in st.session_state:
        st.session_state["first_boot"] = True
        try:
            clear_models()
        except:
            pass
    else:
        st.session_state["first_boot"] = False
    if server_state["in_use"] and st.session_state["first_boot"]:
        st.session_state["available"] = False
    else:
        st.session_state["available"] = True


def setup_local_files():
    "read in local metadata helper files"

    if "llm_dict" not in st.session_state:
        st.session_state["llm_dict"] = pd.read_csv("metadata/llm_list.csv")

    if "corpora_dict" not in st.session_state:
        st.session_state["corpora_dict"] = pd.read_csv("metadata/corpora_list.csv")

    if "db_info" not in st.session_state:
        st.session_state["db_info"] = pd.read_csv("metadata/db_creds.csv")
