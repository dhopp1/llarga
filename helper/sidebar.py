from io import BytesIO
from local_vector_search.misc import pickle_load, pickle_save
import os
import pandas as pd
import shutil
import streamlit as st
from streamlit_server_state import server_state
import time

from helper.lvs import make_new_chat, process_corpus, save_user_settings
from helper.user_management import update_server_state


def sidebar_chats():
    # chats dropdown
    st.sidebar.selectbox(
        "Select chat",
        options=st.session_state["chat_options"],
        index=(
            st.session_state["chat_options"].index(
                st.session_state["user_settings"]["selected_chat_name"]
            )
            if "selected_chat_name" not in st.session_state
            else st.session_state["chat_options"].index(
                st.session_state["selected_chat_name"]
            )
        ),
        key="selected_chat_name",
        help="Which chat history to load",
        on_change=save_user_settings,
    )
    st.session_state["selected_chat_id"] = [
        key
        for key, value in st.session_state["chat_history"].items()
        if value.get("chat_name") == st.session_state["selected_chat_name"]
    ][0]

    # chat buttons
    if "selected_chat_id" in st.session_state:
        with st.sidebar:
            # delete chat button
            # Initial state
            if "show_confirmation" not in st.session_state:
                st.session_state.show_confirmation = False
            if "confirmed" not in st.session_state:
                st.session_state.confirmed = False

            # Function to handle the initial button click
            def show_confirmation_dialog():
                st.session_state.show_confirmation = True

            # Function to handle the confirmation
            def confirm_action():
                st.session_state.confirmed = True
                st.session_state.show_confirmation = False

                # actual deletion
                del st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]
                pickle_save(
                    st.session_state["chat_history"],
                    f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle""",
                )

                if (
                    len(st.session_state["chat_history"]) == 0
                ):  # remove pickle if there are no chats
                    os.remove(
                        f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle"""
                    )

                # Reset the confirmation if needed
                # switching to latest chat, or making a new chat
                if len(st.session_state["chat_history"]) > 0:
                    st.session_state["selected_chat_id"] = max(
                        [
                            k
                            for k, v in st.session_state["chat_history"].items()
                            if k != st.session_state["selected_chat_id"]
                        ]
                    )
                    save_user_settings(
                        selected_chat_name=st.session_state["chat_history"][
                            st.session_state["selected_chat_id"]
                        ]["chat_name"]
                    )
                else:
                    make_new_chat()
                st.session_state.confirmed = False

            # Main button
            if (
                not st.session_state.show_confirmation
                and not st.session_state.confirmed
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.button("New chat ✎", key="new_chat", on_click=make_new_chat)
                with col2:
                    st.button("Delete chat ⌫", on_click=show_confirmation_dialog)

            # Confirmation dialog
            if st.session_state.show_confirmation:
                st.error(
                    "Are you sure you want to delete this chat? This action cannot be undone."
                )
                col1, col2 = st.columns(2)
                with col1:
                    st.button("Yes, I'm Sure", on_click=confirm_action)
                with col2:
                    st.button(
                        "Cancel",
                        on_click=lambda: setattr(
                            st.session_state, "show_confirmation", False
                        ),
                    )

            # Action after confirmation
            if st.session_state.confirmed:
                st.sidebar.info("Chat has been deleted successfully!")
                # actual deletion
                del st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]
                pickle_save(
                    st.session_state["chat_history"],
                    f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle""",
                )

                if (
                    len(st.session_state["chat_history"]) == 0
                ):  # remove pickle if there are no chats
                    os.remove(
                        f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle"""
                    )
                # Reset the confirmation if needed
                st.session_state.confirmed = False
                time.sleep(3)
                st.rerun()
                if False:
                    if len(st.session_state["chat_history"]) > 0:
                        st.session_state["selected_chat_id"] = max(
                            [k for k, v in st.session_state["chat_history"].items()]
                        )
                        st.rerun()
                    else:
                        make_new_chat()
                        st.rerun()


def sidebar_llm_dropdown():
    st.selectbox(
        "Select LLM",
        options=st.session_state["llm_dropdown_options"],
        index=(
            st.session_state["llm_dropdown_options"].index(
                st.session_state["user_settings"]["selected_llm"]
            )
            if "selected_llm" not in st.session_state
            else st.session_state["llm_dropdown_options"].index(
                st.session_state["selected_llm"]
            )
        ),
        help="Which LLM to use. Those ending in `(private)` do not leave our local system, those ending in `(cloud)` will be sent to a cloud provider via API. The latter should not be used for sensitive information.",
        key="selected_llm",
        on_change=save_user_settings,
    )

    st.session_state["is_reasoning_model"] = (
        st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "reasoning_model",
        ]
        .values[0]
    )


def sidebar_llm_api_key():
    st.text_input(
        "Paste API key here",
        value=(
            ""
            if "llm_api_key_user" not in st.session_state
            else st.session_state["llm_api_key_user"]
        ),
        key="llm_api_key_user",
        help="Paste your API key for the cloud LLM provider if availalable. This value will not be saved anywhere.",
    )

    if "llm_api_key" not in st.session_state:
        st.session_state["llm_api_key"] = (
            st.session_state["llm_info"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_llm"],
                "api_key",
            ]
            .values[0]
        )

    # use the user's if provided
    if st.session_state["llm_api_key_user"] != "":
        st.session_state["llm_api_key"] = st.session_state["llm_api_key_user"]
    else:
        st.session_state["llm_api_key"] = (
            st.session_state["llm_info"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_llm"],
                "api_key",
            ]
            .values[0]
        )

    # warn them if the selected one has to provide their own
    if (
        st.session_state["llm_api_key_user"] == ""
        and st.session_state["llm_api_key"] == "API_KEY"
    ):
        st.warning(
            "You must provide your own API key to the selected LLM. Paste it in the `Paste API key here` field above. Its value will not be saved anywhere and will be deleted when you close your session."
        )


def sidebar_temperature_dropdown():
    temp_options = [
        "Most precise",
        "Precise",
        "Balanced",
        "Creative",
        "Most creative",
    ]
    server_state[f"{st.session_state['user_name']}_temperature_string"] = st.selectbox(
        "Model style",
        options=temp_options,
        index=(
            0
            if f"{st.session_state['user_name']}_temperature_string" not in server_state
            else temp_options.index(
                server_state[f"{st.session_state['user_name']}_temperature_string"]
            )
        ),
        help="""
### Most precise
The LLM will be the most predictable and consistent. For anything fact-based, use this setting.
### Precise
The LLM is still mostly precise, but has slightly more freedem in creating its answers.
### Balanced
The LLM is a mixture of creative and precise.
### Creative
The LLM has quite a bit of freedom in creating its answers, which may be inconsistent from question to question.
### Most creative
The LLM has maximum creativity and freedom.
""",
    )

    st.session_state["temperature"] = dict(
        zip(
            ["Most precise", "Precise", "Balanced", "Creative", "Most creative"],
            [0.0, 0.15, 0.4, 0.7, 1.0],
        )
    )[server_state[f"{st.session_state['user_name']}_temperature_string"]]


def sidebar_which_corpus():
    st.selectbox(
        "Currently loaded corpus",
        options=st.session_state["corpus_options"],
        index=(
            st.session_state["corpus_options"].index(
                st.session_state["user_settings"]["selected_corpus"]
            )
            if "selected_corpus" not in st.session_state
            else st.session_state["corpus_options"].index(
                st.session_state["selected_corpus"]
            )
        ),
        key="selected_corpus",
        help="Which corpus to query against. `Workspace` is your personal corpus only you can see. All others are visible to all users. The `Corpus metadata` expander shows the metadata of the documents in the corpus. You can select/unselect documents in via the `Include in queries` column. Only documents checked in that column will be considered relevant for the LLM. You can hover over the table and click the full screen button (like a square) to view the table in a bigger format.",
        on_change=save_user_settings,
    )

    st.session_state["selected_corpus_realname"] = (
        st.session_state["selected_corpus"]
        if "Workspace" not in st.session_state["selected_corpus"]
        else f'Workspace {st.session_state["user_name"]}'
    )


def sidebar_system_prompt():
    try:
        st.session_state["default_system_prompt"] = (
            st.session_state["corpora_list"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_corpus_realname"],
                "system_prompt",
            ]
            .values[0]
        )
    except:
        if st.session_state["selected_corpus"] == "No corpus":
            st.session_state["default_system_prompt"] = (
                st.session_state["settings"]
                .loc[
                    lambda x: x["field"] == "default_no_corpus_system_prompt",
                    "value",
                ]
                .values[0]
            )
        else:
            st.session_state["default_system_prompt"] = (
                st.session_state["settings"]
                .loc[
                    lambda x: x["field"] == "default_corpus_system_prompt",
                    "value",
                ]
                .values[0]
            )

    server_state[f"{st.session_state['user_name']}_system_prompt"] = st.text_input(
        "System prompt",
        value=(
            st.session_state["default_system_prompt"]
            if f"{st.session_state['user_name']}_system_prompt" not in server_state
            else server_state[f"{st.session_state['user_name']}_system_prompt"]
        ),
        help="If you change the system prompt, start a new chat to have it take effect.",
    )

    st.markdown("Default system prompt for this corpus")
    st.markdown("```\n" + st.session_state["default_system_prompt"] + "\n```")

    if st.session_state["chat_history"] == {}:
        make_new_chat()
        st.rerun()


def gen_export_df():
    # create DF of the chat
    # getting chunk sources
    corpora_names = [
        _ if _ != "Workspace" else _ + " " + st.session_state["user_name"]
        for _ in st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "corpus"
        ]
    ]
    st.session_state["source_metadata"] = [None] * len(corpora_names)
    st.session_state["source_content"] = [None] * len(corpora_names)
    for i in range(len(corpora_names)):
        try:
            info = server_state["lvs_corpora"][corpora_names[i]].retrieve_chunks(
                chunk_ids=st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["chunk_ids"][i]
            )
            st.session_state["source_metadata"][i] = info["metadata"]
            st.session_state["source_content"][i] = info["chunks"]
        except:
            pass

    st.session_state["export_df"] = pd.DataFrame(
        {
            "chat name": [st.session_state["selected_chat_name"]]
            * len(
                st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                    "corpus"
                ]
            ),
            "date": [""]
            + [
                _.replace("<br> <sub><sup>", "")
                .replace("</sup></sub>", "")
                .split(" ")[0]
                for _ in st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["times"]
                if _ is not None
            ],
            "time": [""]
            + [
                _.replace("<br> <sub><sup>", "")
                .replace("</sup></sub>", "")
                .split(" ")[1]
                for _ in st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["times"]
                if _ is not None
            ],
            "LLM": st.session_state["chat_history"][
                st.session_state["selected_chat_id"]
            ]["selected_llm"],
            "corpus": st.session_state["chat_history"][
                st.session_state["selected_chat_id"]
            ]["corpus"],
            "model style": st.session_state["chat_history"][
                st.session_state["selected_chat_id"]
            ]["model_style"],
            "role": [
                _["role"]
                for _ in st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["messages"]
            ],
            "content": [
                _["content"]
                for _ in st.session_state["chat_history"][
                    st.session_state["selected_chat_id"]
                ]["messages"]
            ],
            "source_metadata": [
                str(_) if _ is not None else ""
                for _ in st.session_state["source_metadata"]
            ],
            "source_content": [
                str(_) if _ is not None else ""
                for _ in st.session_state["source_content"]
            ],
        }
    )


def sidebar_upload_file():
    st.session_state["uploaded_file"] = st.file_uploader(
        "Upload your own documents",
        type=[".zip", ".docx", ".doc", ".txt", ".pdf", ".csv", ".mp3", ".mp4"],
        help="""Any of: \n\n
- a single metadata.csv file (named exactly `metadata.csv`), with at least one column named `web_filepath` with the web addresses of the .html or .pdf documents
- a single .docx, .doc, .txt., .pdf, .mp3, .mp4, or .wav file
- a .zip file that contains documents zipped inside
- a .zip file that also includes a metadata.csv file in it (named exactly `metadata.csv`), with at least a column named `filename` with the names of the files \n\n
    
If you upload a metadata file, you can include a column in it called `vector_weight`. 1 = normal weight, 0.98 = slightly harder to find this document, 0.5 = twice as hard to find this document, etc. \n\n

Once you've uploaded your file, click `Process corpus`. The system prompt for this corpus will be whatever is currently in the `System prompt` text field under the `LLM parameters` dropdown.
""",
    )

    st.text_input("Name for new corpus", value="Workspace", key="new_corpus_name")

    # show a warning if there is a corpus with this name
    if st.session_state["new_corpus_name"] in list(
        st.session_state["corpora_list"]["name"]
    ):
        st.error(
            "There is already a corpus with this name. If you hit the `Process corpus` button, this corpus will be overwritten with the new one."
        )

    st.button("Process corpus", on_click=process_corpus)


def sidebar_delete_corpus():
    st.session_state["delete_corpus_name"] = st.text_input("Name of corpus to delete")
    st.session_state["delete_corpus_button"] = st.button(
        "Delete corpus", help="This will delete the `Currently loaded corpus`"
    )

    if st.session_state["delete_corpus_button"]:
        if st.session_state["delete_corpus_name"] not in ["No corpus", "Workspace"]:
            try:
                # delete metadata file
                os.remove(
                    f'{st.session_state["corpora_path"]}/metadata_{st.session_state["selected_corpus_realname"]}.csv'
                )
                # delete file directory
                shutil.rmtree(
                    f'{st.session_state["corpora_path"]}/{st.session_state["selected_corpus_realname"]}/'
                )
                # delete embeddings file
                os.remove(
                    f'{st.session_state["corpora_path"]}/embeddings_{st.session_state["selected_corpus_realname"]}.parquet'
                )
                # remove from corpora_list csv
                st.session_state["corpora_list"] = (
                    st.session_state["corpora_list"]
                    .loc[
                        lambda x: x["name"]
                        != st.session_state["selected_corpus_realname"],
                        :,
                    ]
                    .reset_index(drop=True)
                )
                st.session_state["corpora_list"].to_csv(
                    "metadata/corpora_list.csv", index=False
                )

                st.info("Corpus successfully deleted!")
                if (
                    st.session_state["delete_corpus_name"]
                    == st.session_state["selected_corpus"]
                ):
                    st.session_state["selected_corpus"] = "Workspace"
                st.session_state["delete_corpus_name"] = ""
                time.sleep(3)
                st.rerun()
            except:
                pass


def sidebar_export_chat():
    # excel prep
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state["export_df"].to_excel(writer, index=False, sheet_name="Sheet1")
    st.session_state["export_df_excel"] = output.getvalue()
    st.session_state["export_df_excel"]

    # download button
    st.download_button(
        "Export chat history as Excel file",
        data=st.session_state["export_df_excel"],
        file_name="chat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
