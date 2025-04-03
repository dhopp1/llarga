from local_vector_search.misc import pickle_load, pickle_save
import os
import pandas as pd
import shutil
import streamlit as st
import time

from helper.lvs import make_new_chat, process_corpus


def sidebar_chats():
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

    # chats dropdown
    try:
        chat_options = [
            v["chat_name"] for k, v in st.session_state["chat_history"].items()
        ][::-1]
        st.session_state["selected_chat_name"] = st.sidebar.selectbox(
            "Select chat",
            options=chat_options,
            index=0,
            help="Which chat history to load",
        )
        st.session_state["selected_chat_id"] = [
            key
            for key, value in st.session_state["chat_history"].items()
            if value.get("chat_name") == st.session_state["selected_chat_name"]
        ][0]
    except:
        pass

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

            # Main button
            if (
                not st.session_state.show_confirmation
                and not st.session_state.confirmed
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state["new_chat"] = st.button("New chat ✎")
                with col2:
                    st.button("Delete chat ⌫", on_click=show_confirmation_dialog)

                # make a new chat
                if st.session_state["new_chat"]:
                    make_new_chat()
                    st.rerun()

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

                if len(st.session_state["chat_history"]) > 0:
                    st.session_state["selected_chat_id"] = max(
                        [k for k, v in st.session_state["chat_history"].items()]
                    )
                    st.rerun()
                else:
                    make_new_chat()
                    st.rerun()


def sidebar_llm_dropdown():
    if "llm_info" not in st.session_state:
        st.session_state["llm_info"] = pd.read_csv("metadata/llm_list.csv")
        st.session_state["llm_dropdown_options"] = list(
            st.session_state["llm_info"].loc[lambda x: x["display"] == 1, "name"].values
        )

    st.session_state["selected_llm"] = st.selectbox(
        "Select LLM",
        options=st.session_state["llm_dropdown_options"],
        index=0,
        help="Which LLM to use. Those ending in `(private)` do not leave our local system, those ending in `(cloud)` will be sent to a cloud provider via API. The latter should not be used for sensitive information.",
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
    st.session_state["llm_api_key_user"] = st.text_input(
        "Paste API key here",
        help="Paste your API key for the cloud LLM provider if availalble.",
    )

    if "llm_api_key" not in st.session_state:
        st.session_state["llm_api_key"] = (
            st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "api_key"]
            .values[0]
        )

    # use the user's if provided
    if st.session_state["llm_api_key_user"] != "":
        st.session_state["llm_api_key"] = st.session_state["llm_api_key_user"]
    else:
        st.session_state["llm_api_key"] = (
            st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "api_key"]
            .values[0]
        )


def sidebar_temperature_dropdown():
    temp_options = [
        "Most precise",
        "Precise",
        "Balanced",
        "Creative",
        "Most creative",
    ]
    st.session_state["temperature_string"] = st.selectbox(
        "Model style",
        options=temp_options,
        index=(
            0
            if "temperature_string" not in st.session_state
            else temp_options.index(st.session_state["temperature_string"])
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
    )[st.session_state["temperature_string"]]


def sidebar_which_corpus():
    st.session_state["corpora_list"] = pd.read_csv("metadata/corpora_list.csv")
    corpus_options = ["No corpus", "Workspace"] + [
        _
        for _ in list(st.session_state["corpora_list"]["name"])
        if "Workspace" not in _
    ]
    st.session_state["default_corpus"] = (
        st.session_state["users_info"]
        .loc[lambda x: x["user"] == st.session_state["user_name"], "default_corpus"]
        .values[0]
    )

    st.session_state["selected_corpus"] = st.selectbox(
        "Currently loaded corpus",
        options=corpus_options,
        index=(
            corpus_options.index(st.session_state["default_corpus"])
            if "selected_corpus" not in st.session_state
            else corpus_options.index(st.session_state["selected_corpus"])
        ),
        help="Which corpus to query against. `Workspace` is your personal corpus only you can see. All others are visible to all users.",
    )


def sidebar_system_prompt():
    if "default_system_prompt" not in st.session_state:
        try:
            st.session_state["default_system_prompt"] = (
                st.session_state["corpora_list"]
                .loc[
                    lambda x: x["name"] == st.session_state["selected_corpus"],
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

    st.session_state["system_prompt"] = st.text_input(
        "System prompt",
        value=(
            st.session_state["default_system_prompt"]
            if "system_prompt" not in st.session_state
            else st.session_state["system_prompt"]
        ),
        help="If you change the system prompt, start a new chat to have it take effect.",
    )

    if st.session_state["chat_history"] == {}:
        make_new_chat()
        st.rerun()


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
                corpora_path = "corpora"
                if st.session_state["delete_corpus_name"] == "Workspace":
                    corpus_name = f'Workspace {st.session_state["user_name"]}'
                else:
                    corpus_name = st.session_state["delete_corpus_name"]

                # delete metadata file
                os.remove(f"{corpora_path}/metadata_{corpus_name}.csv")
                # delete file directory
                shutil.rmtree(f"{corpora_path}/{corpus_name}/")
                # delete embeddings file
                os.remove(f"{corpora_path}/embeddings_{corpus_name}.parquet")
                # remove from corpora_list csv
                st.session_state["corpora_list"] = (
                    st.session_state["corpora_list"]
                    .loc[lambda x: x["name"] != corpus_name, :]
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
