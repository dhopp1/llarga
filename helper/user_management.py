from datetime import datetime, timedelta
import gc
import hmac
import math
import os
import re
import subprocess as sp
import psutil

from local_rag_llm.db_setup import pg_restore
import pandas as pd
import streamlit as st
from streamlit_server_state import server_state, server_state_lock, no_rerun


def update_server_state(key, value):
    "update the server state variable"
    with no_rerun:
        with server_state_lock[key]:
            server_state[key] = value


def check_password():
    """Check if a user entered the password correctly"""
    # check if it hasn't been used in a while, potentially interrupted while executing
    if "last_used" not in server_state:
        update_server_state("last_used", datetime.now())
    if (datetime.now() - server_state["last_used"]).total_seconds() > 60:
        update_server_state("in_use", False)

    if not (st.session_state["available"]):
        st.error("The LLM is currently generating, try again in a few seconds.")

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
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
    else:
        st.session_state["first_boot"] = False
    if server_state["in_use"] and st.session_state["first_boot"]:
        st.session_state["available"] = False
    else:
        st.session_state["available"] = True

    # boot them if they're logging in again
    if "user_name" in st.session_state:
        if (
            f'{st.session_state["user_name"]}_count' in server_state
            and "count" in st.session_state
        ):
            if (
                server_state[f'{st.session_state["user_name"]}_count']
                != st.session_state["count"]
            ):
                # st.session_state["available"] = False
                st.error("You have logged in on another tab.")
                clear_models()
                st.stop()


def setup_local_files():
    "read in local metadata helper files"

    if "llm_dict" not in st.session_state:
        st.session_state["llm_dict"] = pd.read_csv("metadata/llm_list.csv")
        st.session_state["llm_dict"] = (
            st.session_state["llm_dict"]
            .loc[lambda x: x.display == 1, :]
            .reset_index(drop=True)
        )

    if "corpora_dict" not in st.session_state:
        st.session_state["corpora_dict"] = pd.read_csv("metadata/corpora_list.csv")

    if "db_info" not in st.session_state:
        st.session_state["db_info"] = pd.read_csv("metadata/settings.csv")

    if "master_db_name" not in st.session_state:
        st.session_state["master_db_name"] = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "master_db_name", "value"]
            .values[0]
        )

    if "db_password" not in st.session_state:
        st.session_state["db_password"] = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "password", "value"]
            .values[0]
        )

    if "db_user" not in st.session_state:
        st.session_state["db_user"] = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "username", "value"]
            .values[0]
        )

    if "db_host" not in st.session_state:
        st.session_state["db_host"] = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "host", "value"]
            .values[0]
        )

    if "db_port" not in st.session_state:
        st.session_state["db_port"] = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "port", "value"]
            .values[0]
        )

    if "default_similarity_top_k" not in server_state:
        update_server_state(
            "default_similarity_top_k",
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "similarity_top_k", "value"]
                .values[0]
            ),
        )

    if "default_temperature" not in st.session_state:
        update_server_state(
            "default_temperature",
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "temperature", "value"]
                .values[0]
            ),
        )
    print(f"WOW: {server_state['default_temperature']}")

    if "default_max_new_tokens" not in st.session_state:
        update_server_state(
            "default_max_new_tokens",
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "max_new_tokens", "value"]
                .values[0]
            ),
        )

    if "default_chunk_overlap" not in st.session_state:
        update_server_state(
            "default_chunk_overlap",
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "chunk_overlap", "value"]
                .values[0]
            ),
        )

    if "default_chunk_size" not in st.session_state:
        update_server_state(
            "default_chunk_size",
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "chunk_size", "value"]
                .values[0]
            ),
        )

    # restore DB if there's a backup
    if (
        int(
            st.session_state["db_info"]
            .loc[lambda x: x.field == "restore_db", "value"]
            .values[0]
        )
        == 1
    ):
        if "db_restored" not in server_state:
            if os.path.isfile("corpora/vector_db_dump.sql"):
                pg_restore(
                    host=st.session_state["db_host"],
                    port=st.session_state["db_port"],
                    user=st.session_state["db_user"],
                    password=st.session_state["db_password"],
                    db_name=st.session_state["master_db_name"],
                    filename="corpora/vector_db_dump.sql",
                )
            update_server_state("db_restored", True)

    # ensure corpora metadata files `file_path` columns are correct
    if "corpora_metadata_confirmed" not in server_state:
        file_prefix = (
            st.session_state["db_info"]
            .loc[lambda x: x.field == "corpora_location", "value"]
            .values[0]
        )

        def replace_path(file_path):
            if type(file_path) == str:
                try:
                    name = file_prefix + dir_name + file_path.split("/")[-1]
                except:
                    name = file_prefix + dir_name + file_path.split("\\")[-1]
            else:
                name = ""
            return name

        for file in os.listdir("corpora/"):
            if re.match(r"^metadata_.*\.csv$", file):
                dir_name = re.sub(r"metadata_|\.csv", "", file) + "/"
                tmp = pd.read_csv("corpora/" + file)
                tmp["file_path"] = [replace_path(x) for x in tmp["file_path"]]
                tmp.to_csv("corpora/" + file, index=False)

        update_server_state("corpora_metadata_confirmed", True)

    # set application name and author
    if "app_title" not in server_state:
        update_server_state(
            "app_title",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "app_title", "value"]
            .values[0],
        )

    if "author_name" not in server_state:
        update_server_state(
            "author_name",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "author_name", "value"]
            .values[0],
        )

    if "author_email" not in server_state:
        update_server_state(
            "author_email",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "author_email", "value"]
            .values[0],
        )

    # set default system prompt and context prompt
    if "default_system_prompt" not in server_state:
        update_server_state(
            "default_system_prompt",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "rag_system_prompt", "value"]
            .values[0],
        )

        update_server_state(
            "default_nonrag_system_prompt",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "non_rag_system_prompt", "value"]
            .values[0],
        )

    if "default_context_prompt" not in server_state:
        update_server_state(
            "default_context_prompt",
            st.session_state["db_info"]
            .loc[lambda x: x.field == "context_prompt", "value"]
            .values[0],
        )
