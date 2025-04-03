from datetime import datetime
from local_vector_search.misc import pickle_save
import os
import pandas as pd
import streamlit as st
from streamlit_server_state import server_state
import time

from helper.llamacpp_helper import check_reload_llama_cpp
from helper.llm import gen_llm_response, write_stream
from helper.lvs import load_lvs_corpora
from helper.sidebar import make_new_chat
from helper.user_management import (
    lock_llm,
    unlock_llm,
    unlock_llm_release_queue,
    update_server_state,
)


def ui_title_icon():
    "tab title and icon"
    st.set_page_config(
        page_title=st.session_state["app_title"],
        page_icon="https://www.svgrepo.com/show/375527/ai-platform.svg",
    )


def import_styles():
    "import styles sheet and determine avatars of users"
    with open("styles/style.css") as css:
        st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    st.session_state["user_avatar"] = "https://www.svgrepo.com/show/524211/user.svg"
    st.session_state["assistant_avatar"] = (
        "https://www.svgrepo.com/show/375527/ai-platform.svg"
    )


def initial_placeholder():
    "initial placeholder upon first login"

    if "initialized" not in st.session_state:
        if not (
            os.path.isfile(
                f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle"""
            )
        ):
            st.markdown(
                """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
                unsafe_allow_html=True,
            )
        st.session_state["initialized"] = True

        # load corpora
        load_lvs_corpora()


def user_specific_load():
    "load various defaults for a user"
    if "selected_corpus" not in st.session_state:
        st.session_state["selected_corpus"] = (
            pd.read_csv("metadata/user_list.csv")
            .loc[lambda x: x["user"] == st.session_state["user_name"], "default_corpus"]
            .values[0]
        )


def populate_chat():
    "Display chat messages from history on app rerun"
    st.session_state["message_box"] = st.empty()

    if "initialized" and "selected_chat_id" in st.session_state:
        with st.session_state["message_box"].container():
            for i in range(
                1,
                len(
                    st.session_state["chat_history"][
                        st.session_state["selected_chat_id"]
                    ]["messages"]
                ),
            ):  # 1 to exclude system prompt
                message = st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["messages"][i]
                avatar = (
                    st.session_state["user_avatar"]
                    if message["role"] == "user"
                    else st.session_state["assistant_avatar"]
                )
                message_time = st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["times"][i]

                with st.chat_message(message["role"], avatar=avatar):
                    # reasoning
                    if (
                        st.session_state["chat_history"][
                            st.session_state["selected_chat_id"]
                        ]["reasoning"][i]
                        != ""
                    ):
                        with st.expander("Reasoning"):
                            st.markdown(
                                "<em>"
                                + st.session_state["chat_history"][
                                    st.session_state["selected_chat_id"]
                                ]["reasoning"][i]
                                + "</em>",
                                unsafe_allow_html=True,
                            )

                    # normal response
                    st.markdown(
                        message["content"] + message_time, unsafe_allow_html=True
                    )


def import_chat():
    "logic for user chat"

    # load user chat histories if available
    if "chat_history" in st.session_state:
        populate_chat()

    if prompt := st.chat_input("Enter question"):
        # make a new chat if there is none
        if "selected_chat_id" not in st.session_state:
            make_new_chat()

        # Display user message in chat message container
        prompt_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
        with st.chat_message("user", avatar=st.session_state["user_avatar"]):
            st.button("◼ Stop generating", on_click=unlock_llm_release_queue)
            st.markdown(prompt + prompt_time, unsafe_allow_html=True)

        # Add user message to chat history
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "messages"
        ] += [{"role": "user", "content": prompt}]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "times"
        ] += [prompt_time]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "reasoning"
        ] += [""]

        ### queuing logic
        if (
            ".gguf"
            in st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
            .values[0]
        ):
            # lock the model to perform requests sequentially
            if "llm_generating" not in server_state:
                unlock_llm()
            if "last_used" not in server_state:
                update_server_state("last_used", datetime.now())

            if "exec_queue" not in server_state:
                update_server_state("exec_queue", [st.session_state["user_name"]])

            if len(server_state["exec_queue"]) == 0:
                update_server_state("exec_queue", [st.session_state["user_name"]])
            else:
                if st.session_state["user_name"] not in server_state["exec_queue"]:
                    # add to the queue
                    update_server_state(
                        "exec_queue",
                        server_state["exec_queue"] + [st.session_state["user_name"]],
                    )

            with st.spinner("Query queued..."):
                t = st.empty()
                while (
                    server_state["llm_generating"]
                    or server_state["exec_queue"][0] != st.session_state["user_name"]
                ):
                    # check if it hasn't been used in a while, potentially interrupted while executing
                    if (
                        datetime.now() - server_state["last_used"]
                    ).total_seconds() > 60:
                        if (
                            server_state["exec_queue"][1]
                            == st.session_state["user_name"]
                        ):  # only perform if first in the queue
                            unlock_llm()
                            update_server_state(
                                "exec_queue", server_state["exec_queue"][1:]
                            )  # take the first person out of the queue
                            update_server_state("last_used", datetime.now())

                    t.markdown(
                        f'You are place {server_state["exec_queue"].index(st.session_state["user_name"])} of {len(server_state["exec_queue"]) - 1}'
                    )
                    time.sleep(1)
                t.empty()

            check_reload_llama_cpp()  # load their chosen model

            # lock the model while generating
            lock_llm()
            update_server_state("last_used", datetime.now())

        # stream the LLM's answer
        try:
            with st.chat_message(
                "assistant", avatar=st.session_state["assistant_avatar"]
            ):
                write_stream(
                    gen_llm_response(
                        prompt,
                        messages_input=st.session_state["chat_history"][
                            st.session_state["selected_chat_id"]
                        ]["messages"].copy(),
                    )
                )
        except:
            unlock_llm_release_queue()
            st.error(
                "An error was encountered, the model may not be finished loading, please try again in a few seconds."
            )
            time.sleep(3)
            st.rerun()

        # name this chat if haven't already
        if (
            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "chat_name"
            ]
            == "New chat"
        ):
            if (
                st.session_state["is_reasoning_model"] == 1
            ):  # reasoning models take too long to name, just take the first user's question as the name
                chat_name = prompt
            else:
                messages = st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["messages"].copy()
                messages += [
                    {
                        "role": "user",
                        "content": "Given this chat history, provide a 3-7 word name or phrase summarizing the chat's contents. Don't use quotes in the name.",
                    }
                ]
                chat_name = ""
                for chunk in gen_llm_response(prompt, messages):
                    if "<br> <sub><sup>" not in chunk:
                        chat_name += chunk

            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "chat_name"
            ] = chat_name

        # unlocking the queue
        unlock_llm_release_queue()

        # saving chat history
        pickle_save(
            st.session_state["chat_history"],
            f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle""",
        )
        st.rerun()
