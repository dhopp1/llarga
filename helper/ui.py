from datetime import datetime
import os
import pandas as pd
import pickle
import streamlit as st


def pickle_save(obj, path):
    with open(path, "wb") as fOut:
        pickle.dump(obj, fOut)


def pickle_load(path):
    with open(path, "rb") as input_file:
        obj = pickle.load(input_file)
    return obj


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
    st.session_state[
        "assistant_avatar"
    ] = "https://www.svgrepo.com/show/375527/ai-platform.svg"


def initial_placeholder():
    "initial placeholder upon first login"

    if "intialized" not in st.session_state:
        st.markdown(
            """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
            unsafe_allow_html=True,
        )
        st.session_state["initialized"] = True


def user_specific_load():
    "load various defaults for a user"
    if "selected_corpus" not in st.session_state:
        st.session_state["selected_corpus"] = (
            pd.read_csv("metadata/user_list.csv")
            .loc[lambda x: x["user"] == st.session_state["user_name"], "default_corpus"]
            .values[0]
        )
        if st.session_state["selected_corpus"] == "no_corpus":
            st.session_state["system_prompt"] = (
                st.session_state["settings"]
                .loc[lambda x: x["field"] == "default_no_corpus_system_prompt", "value"]
                .values[0]
            )
        else:  ### !!! have to modify this to take the system prompt of the corpus once those are uploaded
            st.session_state["system_prompt"] = (
                pd.read_csv("metadata/settings.csv")
                .loc[lambda x: x["field"] == "default_corpus_system_prompt", "value"]
                .values[0]
            )


def populate_chat():
    "Display chat messages from history on app rerun"
    st.session_state["message_box"] = st.empty()

    if "initialized" in st.session_state:
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
                    st.markdown(
                        message["content"] + message_time, unsafe_allow_html=True
                    )


def import_chat():
    "logic for user chat"

    # load user chat histories if available
    if "chat_history" not in st.session_state:
        if os.path.isfile(f"""{st.session_state["user_name"]}_chats.pickle"""):
            st.session_state["chat_history"] = pickle_load(
                f"""{st.session_state["user_name"]}_chats.pickle"""
            )
            st.session_state["latest_chat_id"] = max(
                [k for k, v in st.session_state["chat_history"].items()]
            )
        else:
            st.session_state["chat_history"] = {}
            st.session_state["latest_chat_id"] = 0
    else:
        if "selected_chat_id" not in st.session_state:  # first load
            st.session_state["selected_chat_id"] = (
                st.session_state["latest_chat_id"] + 1
            )
            st.session_state["chat_history"][st.session_state["selected_chat_id"]] = {}
            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "messages"
            ] = [{"role": "system", "content": st.session_state["system_prompt"]}]
            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "times"
            ] = [None]

        populate_chat()

    if prompt := st.chat_input("Enter question"):
        # Display user message in chat message container
        prompt_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
        with st.chat_message("user", avatar=st.session_state["user_avatar"]):
            st.markdown(prompt + prompt_time, unsafe_allow_html=True)

        # Add user message to chat history
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "messages"
        ] += [{"role": "user", "content": prompt}]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "times"
        ] += [
            f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
        ]

        # get answer from LLM
        def llm_placeholder(prompt):
            import time

            for i in range(3):
                time.sleep(1)
                yield prompt

            yield f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""

        # stream the LLM's answer
        def write_stream(stream):
            st.session_state["llm_answer"] = ""
            container = st.empty()
            for chunk in stream:
                st.session_state["llm_answer"] += chunk
                container.write(st.session_state["llm_answer"], unsafe_allow_html=True)

        with st.chat_message("assistant", avatar=st.session_state["assistant_avatar"]):
            write_stream(llm_placeholder(prompt))

        # add assistant response to chat history
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "messages"
        ] += [
            {
                "role": "assistant",
                "content": st.session_state["llm_answer"].split("<br> <sub>")[0],
            }
        ]  # don't include time in chat history
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "times"
        ] += ["<br> <sub>" + st.session_state["llm_answer"].split("<br> <sub>")[1]]

        ### !!! have to add source hover to message responses
