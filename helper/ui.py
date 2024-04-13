from datetime import datetime
import time

import pandas as pd
from streamlit_server_state import server_state, no_rerun
import streamlit as st

from helper.user_management import clear_models, update_server_state


def ui_tab():
    "tab title and icon"
    st.set_page_config(
        page_title="Local LLM",
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


def streamed_response(streamer):
    "stream the LLM's response"
    with st.spinner("Thinking..."):
        for token in streamer.response_gen:
            yield token


def export_chat_history():
    "export chat history"
    chat_history = f'*{st.session_state["user_name"]}\'s chat history from {str(datetime.now().date())}*\n\n'

    counter = 1
    for message in server_state[f'{st.session_state["user_name"]} messages']:
        if "source_string" not in message["content"]:
            role = message["role"]
            if role == "user":
                chat_history += f'### {[counter]} {st.session_state["user_name"]}\n\n'
            else:
                chat_history += f"### {[counter]} LLM\n\n"

            chat_history += f'{message["content"]}\n\n'
        # sources
        else:
            if message["content"] != "source_string:NA":
                source_content = message["content"].split("<br>")[0]
                source_content = (
                    source_content.replace("source_string:", "")
                    .replace("### Metadata:", "\n### Metadata:\n")
                    .replace("### Text:", "\n### Text:\n")
                    .replace(" ```", "```")
                    .replace("# Source", f"### {[counter]} Source")
                )

                chat_history += (
                    "_**Sources**_:\n" + "<br>" + message["content"].split("<br>")[1]
                )
                chat_history += "<details>\n"
                chat_history += source_content
                chat_history += "\n</details>\n\n"
            counter += 1

    return chat_history


def initial_placeholder():
    "initial placeholder upon first login"

    if f'model_{st.session_state["db_name"]}' not in server_state:
        st.markdown(
            """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
            unsafe_allow_html=True,
        )


def ui_header():
    "UI header + setting some variables"
    st.title("Local LLM")

    if "master_db_name" not in st.session_state:
        st.session_state["master_db_name"] = "vector_db"

    if "db_name" not in st.session_state:
        st.session_state["db_name"] = (
            st.session_state["user_name"].lower().replace(" ", "_")
        )

    # count which session of the user this is
    if f'{st.session_state["user_name"]}_count' not in server_state:
        update_server_state(f'{st.session_state["user_name"]}_count', 1)
        st.session_state["count"] = 1
    else:
        update_server_state(
            f'{st.session_state["user_name"]}_count',
            server_state[f'{st.session_state["user_name"]}_count'] + 1,
        )
        st.session_state["count"] = server_state[
            f'{st.session_state["user_name"]}_count'
        ]


def ui_upload_docs():
    "UI section for uploading your own documents"

    # upload your own documents
    st.sidebar.markdown(
        "# Upload your own documents",
        help="Enter the name of your corpus in the `Corpus name` field. If named `temporary`, it will be able to be written over after your session.",
    )

    # paste a list of web urls
    st.session_state["own_urls"] = st.sidebar.text_input(
        "URLs",
        value=""
        if "own_urls" not in st.session_state
        else st.session_state["own_urls"],
        help="A comma separated list of URLs.",
    )

    st.session_state["uploaded_file"] = st.sidebar.file_uploader(
        "Upload your own documents",
        type=[".zip", ".docx", ".doc", ".txt", ".pdf", ".csv"],
        help="Upload either a single `metadata.csv` file, with at least one column named `web_filepath` with the web addresses of the .html or .pdf documents, or upload a .zip file that contains a folder named `corpus` with the .csv, .doc, .docx, .txt, or .pdf files inside. You can optionally include a `metadata.csv` file in the zip file at the same level as the `corpus` folder, with at least a column named `filename` with the names of the files. If you want to only include certain page numbers of PDF files, in the metadata include a column called 'page_numbers', with the pages formatted as e.g., '1,6,9:12'.",
    )

    st.session_state["process_corpus_button"] = st.sidebar.button(
        "Process corpus",
        help="Click if you uploaded your own documents or pasted your own URLs.",
    )


def ui_model_params():
    "UI section for selected LLM and corpus model parameters"

    # model params
    st.sidebar.markdown(
        "# Model parameters",
        help="Click the `Reinitialize model` button if you change any of these parameters.",
    )

    # which_llm
    st.session_state["selected_llm"] = st.sidebar.selectbox(
        "Which LLM",
        options=st.session_state["llm_dict"].name,
        index=tuple(st.session_state["llm_dict"].name).index("mistral-docsgpt")
        if "selected_llm" not in st.session_state
        else tuple(st.session_state["llm_dict"].name).index(
            st.session_state["selected_llm"]
        ),
        help="Which LLM to use.",
    )

    # which corpus
    st.session_state["selected_corpus"] = st.sidebar.selectbox(
        "Which corpus",
        options=["None"]
        + sorted(
            [
                x
                for x in list(st.session_state["corpora_dict"].name)
                if "temporary" not in x
                or x == f"temporary_{st.session_state['db_name']}"
            ]
        ),  # don't show others' temporary corpora
        index=0
        if f"""{st.session_state["db_name"]}_which_corpus""" not in server_state
        else tuple(
            ["None"]
            + sorted(
                [
                    x
                    for x in list(st.session_state["corpora_dict"].name)
                    if "temporary" not in x
                    or x == f"temporary_{st.session_state['db_name']}"
                ]
            )
        ).index(
            server_state[f'{st.session_state["db_name"]}_which_corpus']
            if server_state[f'{st.session_state["db_name"]}_which_corpus'] is not None
            else "None"
        ),
        help="Which corpus to contextualize on.",
    )


def ui_advanced_model_params():
    "UI section for advanced model parameters"

    with st.sidebar.expander("Advanced model parameters"):
        # renaming new corpus
        st.session_state["new_corpus_name"] = st.text_input(
            "Uploaded corpus name",
            value=f"temporary_{st.session_state['db_name']}"
            if "new_corpus_name" not in st.session_state
            else st.session_state["new_corpus_name"],
            help="The name of the new corpus you are processing. It must be able to be a SQL database name, so only lower case, no special characters, no spaces. Use underscores.",
        )

        # similarity top k
        st.session_state["similarity_top_k"] = st.slider(
            "Similarity top K",
            min_value=1,
            max_value=20,
            step=1,
            value=4
            if "similarity_top_k" not in st.session_state
            else st.session_state["similarity_top_k"],
            help="The number of contextual document chunks to retrieve for RAG.",
        )

        # n_gpu layers
        st.session_state["n_gpu_layers"] = (
            100
            if "n_gpu_layers" not in st.session_state
            else st.session_state["n_gpu_layers"]
        )

        # temperature
        st.session_state["temperature"] = st.slider(
            "Temperature",
            min_value=0,
            max_value=100,
            step=1,
            value=0
            if "temperature" not in st.session_state
            else st.session_state["temperature"],
            help="How much leeway/creativity to give the model, 0 = least creativity, 100 = most creativity.",
        )

        # max_new tokens
        st.session_state["max_new_tokens"] = st.slider(
            "Max new tokens",
            min_value=16,
            max_value=16000,
            step=8,
            value=512
            if "max_new_tokens" not in st.session_state
            else st.session_state["max_new_tokens"],
            help="How long to limit the responses to (token ≈ word).",
        )

        # context window
        st.session_state["context_window"] = st.slider(
            "Context window",
            min_value=500,
            max_value=50000,
            step=100,
            value=4000
            if "context_window" not in st.session_state
            else st.session_state["context_window"],
            help="How large to make the context window for the LLM. The maximum depends on the model, a higher value might result in context window too large errors.",
        )

        # memory limit
        st.session_state["memory_limit"] = st.slider(
            "Memory limit",
            min_value=80,
            max_value=80000,
            step=8,
            value=2048
            if "memory_limit" not in st.session_state
            else st.session_state["memory_limit"],
            help="How many tokens (words) memory to give the chatbot.",
        )

        # system prompt
        st.session_state["system_prompt"] = st.text_input(
            "System prompt",
            value=""
            if "system_prompt" not in st.session_state
            else st.session_state["system_prompt"],
            help="What prompt to initialize the chatbot with. Hit the `Reset model's memory` button after changing to take effect. Has less impact with RAG queries.",
        )

        # params that affect the vector_db
        st.markdown(
            "# Vector DB parameters",
            help="Changing these parameters will require remaking the vector database and require a bit longer to run. Push the `Reinitialize model and remake DB` button if you change one of these.",
        )

        # chunk overlap
        st.session_state["chunk_overlap"] = st.slider(
            "Chunk overlap",
            min_value=0,
            max_value=1000,
            step=1,
            value=200
            if "chunk_overlap" not in st.session_state
            else st.session_state["chunk_overlap"],
            help="How many tokens to overlap when chunking the documents.",
        )

        # chunk size
        st.session_state["chunk_size"] = st.slider(
            "Chunk size",
            min_value=64,
            max_value=6400,
            step=8,
            value=512
            if "chunk_size" not in st.session_state
            else st.session_state["chunk_size"],
            help="How many tokens per chunk when chunking the documents.",
        )

        st.session_state["reinitialize_remake"] = st.button(
            "Reinitialize model and remake DB",
            help="Click if you make any changes to the vector DB parameters.",
        )

    st.session_state["reinitialize"] = st.sidebar.button(
        "Reinitialize model",
        help="Click if you change the `Which LLM` or `Which corpus` options.",
    )


def ui_reset():
    "UI reset button"

    st.session_state["reset_memory"] = st.sidebar.button(
        "Reset model's memory",
        help="Reset the model's short-term memory to start with a fresh model",
    )


def ui_export_chat_end_session():
    "UI elements, export chat end session and help contact"
    if f'{st.session_state["user_name"]} messages' in server_state:
        st.session_state["export_chat_button"] = st.sidebar.download_button(
            label="Export chat history",
            data=export_chat_history(),
            file_name="chat_history.MD",
            help="Export the session's chat history to a formatted Markdown file. If you don't have a Markdown reader on your computer, post the contents to a [web app](http://editor.md.ipandao.com/en.html)",
        )

    # end session button
    end_session = st.sidebar.button("End session", help="End your session.")
    if end_session:
        clear_models()
        update_server_state(
            f'{st.session_state["user_name"]} messages', []
        )  # reset user's message history
        st.session_state["password_correct"] = False
        st.rerun()
        st.stop()

    # help contact
    st.sidebar.markdown(
        "*For questions on how to use this application or its methodology, please write [Author](mailto:someone@example.com)*",
        unsafe_allow_html=True,
    )


def import_chat():
    "UI element and logic for chat interface"

    if f'model_{st.session_state["db_name"]}' in server_state:
        # Initialize chat history
        if f'{st.session_state["user_name"]} messages' not in server_state:
            update_server_state(f'{st.session_state["user_name"]} messages', [])

        # Display chat messages from history on app rerun
        for message in server_state[f'{st.session_state["user_name"]} messages']:
            avatar = (
                st.session_state["user_avatar"]
                if message["role"] == "user"
                else st.session_state["assistant_avatar"]
            )
            with st.chat_message(message["role"], avatar=avatar):
                if "source_string" not in message["content"]:
                    st.markdown(message["content"], unsafe_allow_html=True)
                else:
                    st.markdown(
                        "Sources: "
                        + "<br>"
                        + message["content"].split("string:")[1].split("<br>")[1],
                        unsafe_allow_html=True,
                        help=message["content"].split("string:")[1].split("<br>")[0],
                    )

        # reset model's memory
        if st.session_state["reset_memory"]:
            if (
                server_state[f'model_{st.session_state["db_name"]}'].chat_engine
                is not None
            ):
                with no_rerun:
                    server_state[
                        f'model_{st.session_state["db_name"]}'
                    ].chat_engine = None
            with st.chat_message(
                "assistant", avatar=st.session_state["assistant_avatar"]
            ):
                st.markdown("Model memory reset!")
            update_server_state(
                f'{st.session_state["user_name"]} messages',
                server_state[f'{st.session_state["user_name"]} messages']
                + [{"role": "assistant", "content": "Model memory reset!"}],
            )

        # Accept user input
        if server_state[f'{st.session_state["db_name"]}_which_corpus'] is None:
            placeholder_text = (
                f"""Query '{st.session_state["selected_llm"]}', not contextualized"""
            )
        else:
            placeholder_text = (
                f"""Query '{st.session_state["selected_llm"]}' contextualized on '"""
                + server_state[f'{st.session_state["db_name"]}_which_corpus']
                + """' corpus"""
            )

        if prompt := st.chat_input(placeholder_text):
            # Display user message in chat message container
            prompt_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
            with st.chat_message("user", avatar=st.session_state["user_avatar"]):
                st.markdown(prompt + prompt_time, unsafe_allow_html=True)
            # Add user message to chat history
            update_server_state(
                f'{st.session_state["user_name"]} messages',
                server_state[f'{st.session_state["user_name"]} messages']
                + [{"role": "user", "content": prompt + prompt_time}],
            )

            # lock the model to perform requests sequentially
            if "in_use" not in server_state:
                update_server_state("in_use", False)

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
                    server_state["in_use"]
                    or server_state["exec_queue"][0] != st.session_state["user_name"]
                ):
                    t.markdown(
                        f'You are place {server_state["exec_queue"].index(st.session_state["user_name"])} of {len(server_state["exec_queue"]) - 1}'
                    )
                    time.sleep(1)
                t.empty()

            # lock the model while generating
            update_server_state("in_use", True)

            # generate response
            response = server_state[
                f'model_{st.session_state["db_name"]}'
            ].gen_response(
                prompt=server_state[f'{st.session_state["user_name"]} messages'][-1][
                    "content"
                ],
                llm=server_state[st.session_state["selected_llm"]],
                similarity_top_k=st.session_state["similarity_top_k"],
                temperature=st.session_state["temperature"],
                max_new_tokens=st.session_state["max_new_tokens"],
                context_window=st.session_state["context_window"],
                use_chat_engine=st.session_state["use_chat_engine"],
                reset_chat_engine=st.session_state["reset_chat_engine"],
                memory_limit=st.session_state["memory_limit"],
                system_prompt=st.session_state["system_prompt"],
                streaming=True,
            )

            # Display assistant response in chat message container
            with st.chat_message(
                "assistant", avatar=st.session_state["assistant_avatar"]
            ):
                st.write_stream(streamed_response(response["response"]))

            # adding sources
            response_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
            with st.chat_message(
                "assistant", avatar=st.session_state["assistant_avatar"]
            ):
                if len(response.keys()) > 1:  # only do if RAG
                    # markdown help way
                    source_string = ""
                    counter = 1
                    for j in list(
                        pd.Series(list(response.keys()))[
                            pd.Series(list(response.keys())) != "response"
                        ]
                    ):
                        # source_string += f"**Source {counter}**:\n\n \t\t{response[j]}\n\n\n\n"
                        metadata_dict = eval(
                            response[j]
                            .split("| source text:")[0]
                            .replace("metadata: ", "")
                        )
                        metadata_string = ""
                        for key, value in metadata_dict.items():
                            if key != "is_csv":
                                metadata_string += f"'{key}': '{value}'\n"

                        source_string += f"""# Source {counter}\n ### Metadata:\n ```{metadata_string}```\n ### Text:\n{response[j].split("| source text:")[1]}\n\n"""
                        counter += 1
                else:
                    source_string = "NA"

                # adding model information
                source_string += "\n# Model parameters\n"
                source_string += f"""```
Which LLM: {st.session_state["selected_llm"]}
Which corpus: {st.session_state["selected_corpus"]}
Similarity top K: {st.session_state["similarity_top_k"]}
Temperature: {st.session_state["temperature"]}
Max new tokens: {st.session_state["max_new_tokens"]}
Context window: {st.session_state["context_window"]}
Memory limit: {st.session_state["memory_limit"]}
System prompt: {st.session_state["system_prompt"]}
Chunk overlap: {st.session_state["chunk_overlap"]}
Chunk size: {st.session_state["chunk_size"]}
```
                """
                st.markdown(
                    "Sources: " + response_time,
                    unsafe_allow_html=True,
                    help=f"{source_string}",
                )

            # unlock the model
            update_server_state("in_use", False)
            update_server_state(
                "exec_queue", server_state["exec_queue"][1:]
            )  # take out of the queue

            # Add assistant response to chat history
            update_server_state(
                f'{st.session_state["user_name"]} messages',
                server_state[f'{st.session_state["user_name"]} messages']
                + [{"role": "assistant", "content": response["response"].response}],
            )
            update_server_state(
                f'{st.session_state["user_name"]} messages',
                server_state[f'{st.session_state["user_name"]} messages']
                + [
                    {
                        "role": "assistant",
                        "content": f"source_string:{source_string}{response_time}",
                    }
                ],
            )
