import psutil
import re
import streamlit as st
from streamlit_server_state import server_state
import subprocess
import time

from helper.user_management import update_server_state


def start_llama_cpp_server(name, llm_info_df):
    "start a llama cpp server of a given model. Returns pid of process"
    print("started server func")

    llm_filepath = llm_info_df.loc[lambda x: x["name"] == name, "model_name"].values[0]
    port = re.search(
        r":(\d+)", llm_info_df.loc[lambda x: x["name"] == name, "llm_url"].values[0]
    ).group(1)

    process = subprocess.Popen(
        ["llama-server", "-m", llm_filepath, "--port", port, "--no-warmup"],
        start_new_session=True,
    )
    print(f"pid of llama cpp model: {process.pid}")

    return process.pid


def stop_llama_cpp_server(pid):
    "kill a running llama cpp server"
    process = psutil.Process(pid)
    process.kill()
    del process


def check_reload_llama_cpp():
    "check if a local LLM is loaded and load if not, change if it's a different one"

    if "selected_llm" in st.session_state:

        # if llm changed and its local and not already loaded, kill the old one and load it
        # first check if it's a local llm
        if (
            ".gguf"
            in st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
            .values[0]
        ):

            # if no model loaded, load the selected one
            if "llama_cpp_pid" not in server_state:
                update_server_state("llama_cpp_name", st.session_state["selected_llm"])
                update_server_state(
                    "llama_cpp_pid",
                    start_llama_cpp_server(
                        name=st.session_state["selected_llm"],
                        llm_info_df=st.session_state["llm_info"],
                    ),
                )
            else:  # if a model is loaded, unload the old one and load the new one if they're different
                if "llama_cpp_name" in server_state:
                    if (
                        server_state["llama_cpp_name"]
                        != st.session_state["selected_llm"]
                    ):
                        with st.spinner(
                            "Waiting for generation to finish to switch model..."
                        ):
                            if "llm_generating" not in server_state:
                                update_server_state("llm_generating", False)

                            if not (server_state["llm_generating"]):
                                stop_llama_cpp_server(server_state["llama_cpp_pid"])
                                update_server_state(
                                    "llama_cpp_name", st.session_state["selected_llm"]
                                )
                                update_server_state(
                                    "llama_cpp_pid",
                                    start_llama_cpp_server(
                                        name=st.session_state["selected_llm"],
                                        llm_info_df=st.session_state["llm_info"],
                                    ),
                                )
                            else:
                                time.sleep(5)
                                st.rerun()
