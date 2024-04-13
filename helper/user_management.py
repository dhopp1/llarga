from datetime import datetime, timedelta
import gc
import hmac
import math
import subprocess as sp
import psutil

import pandas as pd
import streamlit as st
from streamlit_server_state import server_state, server_state_lock, no_rerun
import torch


def check_password():
    """Check if a user entered the password correctly"""
    if not (st.session_state["available"]):
        # people currently using it
        current_users = sorted([k for k, v in server_state["locked"].items() if v])
        current_emails = [
            st.session_state["users_list"]
            .loc[lambda x: x.user == user, "email"]
            .values[0]
            for user in current_users
        ]

        error_string = "Application in use by:\n\n"

        for i in range(len(current_users)):
            error_string += f"""[{current_users[i]}](mailto:{current_emails[i]}) (reserved for {server_state["last_used_threshold"][current_users[i]]} minutes)\n\n"""

        error_string += f"""Refresh in {min(server_state["last_used_threshold"].values())} minutes, if someone has stopped using it you will be able to log in."""
        st.error(error_string)

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


def record_use(future_lock=False, free_up=False):
    "record a usage, future lock to put it in the future for long running processes"
    with no_rerun:
        with server_state_lock["last_used"]:
            if future_lock:
                server_state["last_used"][
                    st.session_state["user_name"]
                ] = datetime.now() + timedelta(hours=2, minutes=0)
            elif free_up:
                server_state["last_used"][
                    st.session_state["user_name"]
                ] = datetime.now() - timedelta(hours=6, minutes=0)
            else:
                server_state["last_used"][
                    st.session_state["user_name"]
                ] = datetime.now()


def clear_models():
    if f'model_{st.session_state["db_name"]}' in server_state:
        try:
            server_state[f'model_{st.session_state["db_name"]}'].close_connection()
        except:
            pass
        del server_state[f'model_{st.session_state["db_name"]}']
        gc.collect()


def calc_cuda(n_users):
    "how many users can the GPU support"

    command = "nvidia-smi --query-gpu=memory.free --format=csv"
    memory_free_info = (
        sp.check_output(command.split()).decode("ascii").split("\n")[:-1][1:]
    )
    memory_free_value = [int(x.split()[0]) for i, x in enumerate(memory_free_info)][0]

    command = "nvidia-smi --query-gpu=memory.total --format=csv"
    memory_total_info = (
        sp.check_output(command.split()).decode("ascii").split("\n")[:-1][1:]
    )
    memory_total_value = [int(x.split()[0]) for i, x in enumerate(memory_total_info)][0]

    memory_used_value = memory_total_value - memory_free_value

    return math.floor(memory_total_value / (memory_used_value / n_users))


def calc_mps(n_users):
    "how many users can the MPS backend support"

    return math.floor(
        psutil.virtual_memory()[0]
        * 1.15
        / (torch.mps.driver_allocated_memory() / n_users)
    )


def calc_max_users(n_users):
    "given current existing user(s), how many can the machine support"

    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = "mps"
    else:
        device = "cpu"

    if device == "cpu":
        max_users = 1
    elif device == "mps":
        max_users = calc_mps(n_users)
    elif device == "cuda":
        max_users = calc_cuda(n_users)

    return max_users


def determine_availability():
    "determine if the application is available to the user"

    # how long between inactivity to lock a users session for in minutes
    if "last_used_threshold" not in st.session_state:
        st.session_state["last_used_threshold"] = 3

    if "max_users" not in server_state:
        update_server_state("max_users", 1)

    # user list
    if "users_list" not in st.session_state:
        st.session_state["users_list"] = pd.read_csv("metadata/user_list.csv")

    # if never been used, available
    if "last_used" not in server_state:
        st.session_state["available"] = True
        if "user_name" in st.session_state:
            update_server_state(
                "last_used", {st.session_state["user_name"]: datetime.now()}
            )
            update_server_state(
                "last_used_threshold",
                {
                    st.session_state["user_name"]: st.session_state[
                        "last_used_threshold"
                    ]
                },
            )
        else:
            update_server_state("last_used", {})
            update_server_state("last_used_threshold", {})
    else:
        if "user_name" in st.session_state:
            if st.session_state["user_name"] is not None:
                with no_rerun:
                    with server_state_lock["last_used"]:
                        # if exists, don't update, if not, give it an initialize value an hour ago
                        if (
                            st.session_state["user_name"]
                            not in server_state["last_used"]
                        ):
                            server_state["last_used"][
                                st.session_state["user_name"]
                            ] = datetime.now() - timedelta(hours=60)

                    # update their personal lockout threshold
                    with server_state_lock["last_used_threshold"]:
                        server_state["last_used_threshold"][
                            st.session_state["user_name"]
                        ] = st.session_state["last_used_threshold"]

        with no_rerun:
            with server_state_lock["locked"]:
                server_state["locked"] = {}
                for key, value in server_state["last_used"].items():
                    server_state["locked"][key] = (
                        datetime.now() - value
                    ).total_seconds() < server_state["last_used_threshold"][key] * 60

        # check if override boot
        with server_state_lock["last_used"]:
            if "override" in st.session_state:
                if st.session_state["override"]:
                    # set longest ago user to a long time ago to make them boot eligible
                    bootable_user = [
                        k
                        for k, v in server_state["last_used"].items()
                        if v == sorted(set(server_state["last_used"].values()))[1]
                    ][0]
                    server_state["last_used"][
                        bootable_user
                    ] = datetime.now() - timedelta(hours=12)
                    server_state["locked"][bootable_user] = False

        # is there a free spot and the model isn't currently generating
        if "in_use" not in server_state:
            update_server_state("in_use", False)
        if server_state["in_use"]:
            st.session_state["available"] = False
        else:
            st.session_state["available"] = (
                sum(server_state["locked"].values()) < server_state["max_users"]
            )

        # check if you are already in the list
        if "user_name" in st.session_state:
            if st.session_state["user_name"] is not None:
                if server_state["locked"][st.session_state["user_name"]]:
                    st.session_state["available"] = True


def manage_boot():
    "check if it's the frist boot of the user and if the current user is boot eligible"

    # checking if first boot of user
    if "first_boot" not in st.session_state:
        st.session_state["first_boot"] = True
        clear_models()
        # first boot of server
        if "last_user" not in server_state:
            update_server_state("queue", [st.session_state["user_name"]])
        else:
            # add new user to queue, causing an update to other users' sessions
            update_server_state(
                "queue", server_state["queue"] + [st.session_state["user_name"]]
            )

        with server_state_lock["last_user"]:
            server_state["last_user"] = st.session_state["user_name"]
    else:
        st.session_state["first_boot"] = False

    # checking if first boot of server
    if "first_boot" not in server_state:
        update_server_state("first_boot", True)
    else:
        update_server_state("first_boot", False)

    # Do not continue if a new user has booted off this one
    if (
        not (server_state["locked"][st.session_state["user_name"]])
        and len(server_state["queue"]) > server_state["max_users"]
    ):
        # eligible boots
        eligible_boots = [
            x for x in server_state["queue"] if not (server_state["locked"][x])
        ]
        if eligible_boots[0] == st.session_state["user_name"]:
            st.error(
                f"""[{server_state["queue"][-1]}](mailto:{st.session_state["users_list"].loc[lambda x: x.user == server_state["queue"][-1], "email"].values[0]}) has logged on. Refresh in {min(server_state["last_used_threshold"].values())} minutes, if someone has stopped using it you will be able to log in."""
            )
            clear_models()

            update_server_state(
                "queue", [x for x in server_state["queue"] if x != eligible_boots[0]]
            )

            st.stop()


def setup_local_files():
    "read in local metadata helper files"

    if "llm_dict" not in st.session_state:
        st.session_state["llm_dict"] = pd.read_csv("metadata/llm_list.csv")

    if "corpora_dict" not in st.session_state:
        st.session_state["corpora_dict"] = pd.read_csv("metadata/corpora_list.csv")

    if "db_info" not in st.session_state:
        st.session_state["db_info"] = pd.read_csv("metadata/db_creds.csv")
