from datetime import datetime
from local_vector_search.misc import pickle_load, pickle_save
import os
import pandas as pd
import streamlit as st
from streamlit_server_state import server_state
import time

from helper.llamacpp_helper import check_reload_llama_cpp
from helper.llm import gen_llm_response, write_stream
from helper.lvs import load_lvs_corpora, save_user_settings
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

    if ("initialized" not in st.session_state) or (
        "New chat" in st.session_state["selected_chat_name"]
    ):  # show if new chat or first log in
        st.session_state["initialized"] = True

        # load corpora
        load_lvs_corpora()

    ### load user options
    # chat history
    if "chat_history" not in st.session_state:
        if os.path.isfile(
            f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle"""
        ):
            st.session_state["chat_history"] = pickle_load(
                f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle"""
            )
            st.session_state["latest_chat_id"] = max(
                [k for k, v in st.session_state["chat_history"].items()]
            )
        else:
            st.session_state["chat_history"] = {}
            st.session_state["latest_chat_id"] = 0
            make_new_chat()

    st.session_state["chat_options"] = [
        v["chat_name"] for k, v in st.session_state["chat_history"].items()
    ][::-1]

    # llm
    if "llm_info" not in st.session_state:
        st.session_state["llm_info"] = pd.read_csv("metadata/llm_list.csv")
        st.session_state["llm_dropdown_options"] = list(
            st.session_state["llm_info"].loc[lambda x: x["display"] == 1, "name"].values
        )

    # corpora
    st.session_state["corpora_list"] = pd.read_csv("metadata/corpora_list.csv")
    st.session_state["corpus_options"] = ["No corpus", "Workspace"] + [
        _
        for _ in list(st.session_state["corpora_list"]["name"])
        if "Workspace" not in _
    ]

    st.session_state["default_corpus"] = (
        st.session_state["users_info"]
        .loc[lambda x: x["user"] == st.session_state["user_name"], "default_corpus"]
        .values[0]
    )

    # user settings pickle file
    if "user_settings" not in st.session_state:
        try:
            st.session_state["user_settings"] = pickle_load(
                f'metadata/user_settings/{st.session_state["user_name"]}.pickle'
            )
        except:
            st.session_state["user_settings"] = {}
            st.session_state["user_settings"]["selected_llm"] = st.session_state[
                "llm_dropdown_options"
            ][
                0
            ]  # default LLM is first one
            st.session_state["user_settings"]["selected_chat_name"] = st.session_state[
                "chat_history"
            ][st.session_state["latest_chat_id"]][
                "chat_name"
            ]  # default chat name is latest one
            st.session_state["user_settings"]["selected_corpus"] = (
                st.session_state["users_info"]
                .loc[
                    lambda x: x["user"] == st.session_state["user_name"],
                    "default_corpus",
                ]
                .values[0]
            )  # default loaded corpus is the one specified for the user
            st.session_state["user_settings"][
                "temperature_string"
            ] = "Most precise"  # default is most precise
            # default system prompt is the one for the corpus
            if st.session_state["user_settings"]["selected_corpus"] == "No corpus":
                st.session_state["user_settings"]["system_prompt"] = (
                    st.session_state["settings"]
                    .loc[
                        lambda x: x["field"] == "default_no_corpus_system_prompt",
                        "value",
                    ]
                    .values[0]
                )
            else:
                st.session_state["user_settings"]["system_prompt"] = (
                    st.session_state["corpora_list"]
                    .loc[
                        lambda x: x["name"]
                        == st.session_state["user_settings"]["selected_corpus"],
                        "system_prompt",
                    ]
                    .values[0]
                )
    else:
        st.session_state.selected_chat_name = st.session_state["user_settings"][
            "selected_chat_name"
        ]

    # initialize a display_metadata object
    if "display_metadata" not in st.session_state["user_settings"]:
        st.session_state["user_settings"]["display_metadata"] = {}
    for name in st.session_state["corpora_list"]["name"]:
        # add it if it's a new corpus
        if name not in st.session_state["user_settings"]["display_metadata"]:
            st.session_state["user_settings"]["display_metadata"][name] = pd.read_csv(
                f"""{st.session_state["corpora_path"]}/metadata_{name}.csv"""
            )
            st.session_state["user_settings"]["display_metadata"][
                name
            ] = st.session_state["user_settings"]["display_metadata"][name].loc[
                :,
                [
                    _
                    for _ in st.session_state["user_settings"]["display_metadata"][
                        name
                    ].columns
                    if _ not in ["filepath"]
                ],
            ]
            st.session_state["user_settings"]["display_metadata"][name][
                "Include in queries"
            ] = True


def metadata_tab():
    st.text_input("", key="llm_select_metadata_prompt")
    st.button(
        "Select documents with LLM",
        key="llm_select_metadata_button",
        help="Ask for a subset of documents in natural language based off the metadata. A failure to parse the LLMs response will select all the documents.",
    )

    if st.session_state["selected_corpus"] != "No corpus":
        st.session_state["display_metadata"] = st.data_editor(
            st.session_state["user_settings"]["display_metadata"][
                st.session_state["selected_corpus_realname"]
            ],
            column_config={
                "Include in queries": st.column_config.CheckboxColumn(
                    "Include in queries"
                )
            },
            disabled=[
                col
                for col in st.session_state["user_settings"]["display_metadata"][
                    st.session_state["selected_corpus_realname"]
                ].columns
                if col != "Include in queries"
            ],
            hide_index=True,
        )

        # select all or unselect all
        def select_all():
            st.session_state["display_metadata"]["Include in queries"] = True
            save_user_settings()

        def unselect_all():
            st.session_state["display_metadata"]["Include in queries"] = False
            save_user_settings()

        st.button("Select all", key="select_all_button", on_click=select_all)
        st.button("Unselect all", key="unselect_all_button", on_click=unselect_all)
        st.button(
            "Save selection",
            on_click=save_user_settings,
            help="Click to save your selection.",
        )

    if st.session_state["llm_select_metadata_button"]:
        metadata_button_messages = [
            {
                "role": "system",
                "content": f"""Given this metadata file, determine which entries/documents the user is interested in and respond with a comma-separated list of those text_ids. Respond with only the list, no other commentary. Here is the metadata file: {st.session_state["display_metadata"].drop(["Include in queries"], axis=1).to_markdown(index=False)}""",
            },
            {
                "role": "user",
                "content": f"""Here is the user's query: '{st.session_state["llm_select_metadata_prompt"]}""",
            },
        ]
        llm_selection = ""
        with st.spinner("Thinking..."):
            for chunk in gen_llm_response("", metadata_button_messages):
                if "<br> <sub><sup>" not in chunk:
                    llm_selection += chunk
        try:
            text_ids = [int(_) for _ in llm_selection.split(",")]
        except:
            try:
                text_ids = [
                    int(_) for _ in llm_selection.split("</think>")[1].split(",")
                ]
            except:
                text_ids = list(st.session_state["display_metadata"]["text_id"].values)
        st.session_state["display_metadata"]["Include in queries"] = False
        st.session_state["display_metadata"].loc[
            lambda x: x["text_id"].isin(text_ids), "Include in queries"
        ] = True
        save_user_settings()
        st.rerun()


def run_batch_query():
    if st.session_state["batch_query_button"]:
        with st.sidebar:
            status = st.empty()
            progress = st.progress(0)

        prompts = ["Hello", "Hello again"]
        counter = 0
        for prompt in prompts:
            progress.progress(counter / len(prompts))
            status.text(f"Processing batch query: {counter}/{len(prompts)}")
            chat_loop(prompt, use_memory=False)
            counter += 1
        progress.progress(counter / len(prompts))
        status.info(
            "Batch query complete! Download results by clicking the `Export chat history as Excel file` button."
        )


def populate_chat():
    "Display chat messages from history on app rerun"
    st.session_state["message_box"] = st.empty()

    if "initialized" and "selected_chat_id" in st.session_state:
        with st.session_state["message_box"].container():
            # show initialized text if no messages
            if (
                len(
                    st.session_state["chat_history"][
                        st.session_state["selected_chat_id"]
                    ]["messages"]
                )
                == 1
            ):
                st.markdown(
                    """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
                    unsafe_allow_html=True,
                )

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
                        message["content"]
                        + (message_time if message["role"] == "user" else ""),
                        unsafe_allow_html=True,
                    )

                    # sources
                    if message["role"] == "assistant":
                        source_string = f"""
## General information
- LLM: `{st.session_state["export_df"].loc[i, "LLM"]}`
- Corpus: `{st.session_state["export_df"].loc[i, "corpus"]}`
- Model style: `{st.session_state["export_df"].loc[i, "model style"]}`
"""
                        # RAG
                        if (
                            st.session_state["chat_history"][
                                st.session_state["selected_chat_id"]
                            ]["corpus"][i]
                            != "No corpus"
                        ):
                            source_string += "\n\n## Sources\n"

                            metadata = [
                                _
                                for _ in eval(
                                    st.session_state["export_df"].loc[
                                        i, "source_metadata"
                                    ]
                                )
                            ]
                            content = [
                                _
                                for _ in eval(
                                    st.session_state["export_df"].loc[
                                        i, "source_content"
                                    ]
                                )
                            ]
                            for j in range(len(metadata)):
                                # metadata
                                source_string += (
                                    f"\n**Chunk {j+1}**\n"
                                    + "```\nmetadata\n"
                                    + "\n".join(
                                        [f"{_.strip()}" for _ in metadata[j].split("|")]
                                    )
                                    + "\n```\n"
                                )

                                # content
                                source_string += "```\n" + content[j] + "\n```"

                        st.markdown(
                            "Sources: " + message_time,
                            unsafe_allow_html=True,
                            help=source_string,
                        )


def chat_loop(prompt, use_memory=True):
    # make a new chat if there is none
    if "selected_chat_id" not in st.session_state:
        make_new_chat()

    # Display user message in chat message container
    prompt_time = (
        f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
    )
    with st.chat_message("user", avatar=st.session_state["user_avatar"]):
        try:
            st.button(
                "◼ Stop generating",
                key="stop_generating_button",
                on_click=unlock_llm_release_queue,
            )
        except:
            pass
        st.markdown(prompt + prompt_time, unsafe_allow_html=True)

    # Add user message to chat history
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "messages"
    ] += [{"role": "user", "content": prompt}]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]]["times"] += [
        prompt_time
    ]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "reasoning"
    ] += [""]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "corpus"
    ] += [""]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "chunk_ids"
    ] += [[]]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "selected_llm"
    ] += [st.session_state["selected_llm"]]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "model_style"
    ] += [st.session_state["temperature_string"]]

    ### queuing logic
    if (
        ".gguf"
        in st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "model_name",
        ]
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
                if (datetime.now() - server_state["last_used"]).total_seconds() > 60:
                    if (
                        server_state["exec_queue"][1] == st.session_state["user_name"]
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
        with st.chat_message("assistant", avatar=st.session_state["assistant_avatar"]):
            if use_memory:
                messages_input = st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["messages"].copy()
            else:
                messages_input = [
                    st.session_state["chat_history"][
                        st.session_state["selected_chat_id"]
                    ]["messages"].copy()[0],
                    st.session_state["chat_history"][
                        st.session_state["selected_chat_id"]
                    ]["messages"].copy()[-1],
                ]
            write_stream(
                gen_llm_response(
                    prompt,
                    messages_input=messages_input,
                )
            )
    except:
        if (
            ".gguf"
            in st.session_state["llm_info"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_llm"],
                "model_name",
            ]
            .values[0]
        ):
            unlock_llm_release_queue()
        st.error(
            "An error was encountered, the model may not be finished loading, please try again in a few seconds."
        )
        time.sleep(3)
        st.rerun()

    # name this chat if haven't already
    if (
        "New chat"
        in st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "chat_name"
        ]
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

            # no duplicate chat names
            if (
                chat_name
                in [
                    v["chat_name"] for k, v in st.session_state["chat_history"].items()
                ][::-1]
            ):
                chat_name += " 2"

        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "chat_name"
        ] = chat_name

        save_user_settings(selected_chat_name=chat_name)

    # unlocking the queue
    if (
        ".gguf"
        in st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "model_name",
        ]
        .values[0]
    ):
        unlock_llm_release_queue()

    # saving chat history
    pickle_save(
        st.session_state["chat_history"],
        f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle""",
    )


def import_chat():
    "logic for user chat"

    # load user chat histories if available
    if "chat_history" in st.session_state:
        populate_chat()

    if prompt := st.chat_input("Enter question"):
        chat_loop(prompt)
        st.rerun()
