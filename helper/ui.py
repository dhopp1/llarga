from datetime import datetime, timedelta
import time
import math

from local_rag_llm.db_setup import pg_dump
import os
import pandas as pd
from streamlit_server_state import server_state, no_rerun
import streamlit as st

from helper.user_management import clear_models, update_server_state
from helper.agents import available_countries, available_languages


def ui_tab():
    "tab title and icon"
    st.set_page_config(
        page_title=server_state["app_title"],
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


def streamed_response(streamer):
    "stream the LLM's response"
    stop_token_start = ["system", "user", "assistant"]
    stop_token_end = ":"

    with st.spinner("Thinking..."):
        prev_token = ""
        hold_token = ""
        st.session_state["assistant_answer"] = ""
        st.session_state["stop_displaying"] = False
        counter = 0
        for token in streamer.response_gen:
            if ((prev_token in stop_token_start) and (token == stop_token_end)) or (
                st.session_state["stop_displaying"]
            ):
                if counter == 0:
                    st.error("Still thinking...")
                else:
                    yield ""
                st.session_state["stop_displaying"] = True
                counter += 1
            elif token in stop_token_start:
                hold_token = token
            else:
                yield hold_token + token
                st.session_state["assistant_answer"] += hold_token + token
                hold_token = ""
            prev_token = token


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
    st.title(server_state["app_title"])

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
        help="Enter the name of your corpus in the `Corpus name` field. If named `temporary`, it will be able to be written over after your session. For Google, you can create a corpus by searching Google or Google News first, which will automatically create a corpus based on your chosen search parameters.",
    )

    # paste a list of web urls
    with st.sidebar.expander("URL(s)"):
        with no_rerun:
            server_state[f'{st.session_state["user_name"]}_own_urls'] = st.text_input(
                "URLs",
                value=(
                    ""
                    if f'{st.session_state["user_name"]}_own_urls' not in server_state
                    else server_state[f'{st.session_state["user_name"]}_own_urls']
                ),
                help="A comma separated list of URLs.",
            )

        server_state[f'{st.session_state["user_name"]}_own_urls_prefix'] = (
            st.text_input(
                "URL prefix",
                value=(
                    ""
                    if f'{st.session_state["user_name"]}_own_urls_prefix'
                    not in server_state
                    else server_state[
                        f'{st.session_state["user_name"]}_own_urls_prefix'
                    ]
                ),
                help="If you would like to get not just the URL provided above, but all links from that page, put here the page prefix for those outward URLs. For instance, say I wanted to process all the pages of documentation for Scikit Learn. I would put `https://scikit-learn.org/stable/user_guide.html` in the field above, then `https://scikit-learn.org/stable/` in this field, because that is the prefix to all the URLs on the user guide site.",
            )
        )

        server_state[f'{st.session_state["user_name"]}_own_urls_include_https'] = (
            st.checkbox(
                "Include HTTPS links?",
                value=(
                    False
                    if f'{st.session_state["user_name"]}_own_urls_include_https'
                    not in server_state
                    else server_state[
                        f'{st.session_state["user_name"]}_own_urls_include_https'
                    ]
                ),
                help="If getting all the links from a page, whether to include https links on that page or just prefixed links.",
            )
        )

    # upload file
    st.session_state["uploaded_file"] = st.sidebar.file_uploader(
        "Upload your own documents",
        type=[".zip", ".docx", ".doc", ".txt", ".pdf", ".csv"],
        help="Upload either a single `metadata.csv` file, with at least one column named `web_filepath` with the web addresses of the .html or .pdf documents, or upload a .zip file that contains a folder named `corpus` with the .csv, .doc, .docx, .txt, or .pdf files inside. You can optionally include a `metadata.csv` file in the zip file at the same level as the `corpus` folder, with at least a column named `filename` with the names of the files. If you want to only include certain page numbers of PDF files, in the metadata include a column called 'page_numbers', with the pages formatted as e.g., '1,6,9:12'.",
    )

    # google news
    with st.sidebar.expander("Google"):
        with no_rerun:
            # google or google news
            server_state[f'{st.session_state["user_name"]}_gn_search'] = st.selectbox(
                "Google source",
                options=["Google search", "Google News"],
                index=(
                    1
                    if f'{st.session_state["user_name"]}_gn_search' not in server_state
                    else ["Google search", "Google News"].index(
                        server_state[f'{st.session_state["user_name"]}_gn_search']
                    )
                ),
                help="Whether to search regular Google or Google News.",
            )

            # google news language
            server_state[f'{st.session_state["user_name"]}_gn_language'] = st.selectbox(
                "Google language",
                options=sorted([x.title() for x in list(available_languages.keys())]),
                index=(
                    sorted([x.title() for x in list(available_languages.keys())]).index(
                        "English"
                    )
                    if f'{st.session_state["user_name"]}_gn_language'
                    not in server_state
                    else sorted(
                        [x.title() for x in list(available_languages.keys())]
                    ).index(
                        server_state[f'{st.session_state["user_name"]}_gn_language']
                    )
                ),
                help="Which language to search Google in.",
            )

            # google news country
            server_state[f'{st.session_state["user_name"]}_gn_country'] = st.selectbox(
                "Google country",
                options=sorted(list(available_countries.keys())),
                index=(
                    sorted(list(available_countries.keys())).index("United States")
                    if f'{st.session_state["user_name"]}_gn_country' not in server_state
                    else sorted(list(available_countries.keys())).index(
                        server_state[f'{st.session_state["user_name"]}_gn_country']
                    )
                ),
                help="Which country to search Google in.",
            )

            # google news max results
            server_state[f'{st.session_state["user_name"]}_gn_max_results'] = (
                st.selectbox(
                    "Google number results",
                    options=list(range(1, 21)),
                    index=(
                        list(range(1, 21)).index(5)
                        if f'{st.session_state["user_name"]}_gn_max_results'
                        not in server_state
                        else list(range(1, 21)).index(
                            server_state[
                                f'{st.session_state["user_name"]}_gn_max_results'
                            ]
                        )
                    ),
                    help="How many results from Google to index.",
                )
            )

            # google news time range
            server_state[f'{st.session_state["user_name"]}_gn_date_range'] = (
                st.date_input(
                    "Google News date range",
                    format="DD.MM.YYYY",
                    value=(datetime.today() - timedelta(days=7), datetime.now()),
                    help="What time range to search Google News (not applicable to normal search).",
                )
            )

            # google news search term
            server_state[f'{st.session_state["user_name"]}_gn_query'] = st.text_input(
                "Google query",
                value=(
                    ""
                    if f'{st.session_state["user_name"]}_gn_query' not in server_state
                    else server_state[f'{st.session_state["user_name"]}_gn_query']
                ),
                help="Google query.",
            )

            # google news site list
            server_state[f'{st.session_state["user_name"]}_gn_site_list'] = (
                st.text_input(
                    "Google site list",
                    value=(
                        ""
                        if f'{st.session_state["user_name"]}_gn_site_list'
                        not in server_state
                        else server_state[
                            f'{st.session_state["user_name"]}_gn_site_list'
                        ]
                    ),
                    help="Which websites you want to search Google for. Pass a comma separated list for multiple sites, e.g.,: `bbc.com,cnn.com`",
                )
            )

    # process corpus button
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
    with no_rerun:
        server_state[f'{st.session_state["user_name"]}_selected_llm'] = (
            st.sidebar.selectbox(
                "Which LLM",
                options=st.session_state["llm_dict"].name,
                index=(
                    0
                    if f'{st.session_state["user_name"]}_selected_llm'
                    not in server_state
                    else tuple(st.session_state["llm_dict"].name).index(
                        server_state[f'{st.session_state["user_name"]}_selected_llm']
                    )
                ),
                help="Which LLM to use.",
            )
        )

    # which corpus
    with no_rerun:
        prefix_text = "Which corpus to contextualize on."
        if (
            f'{st.session_state["user_name"]}_corpus_help_text' not in server_state
            or f'{st.session_state["user_name"]}_selected_corpus' not in server_state
        ):  # first run
            server_state[f'{st.session_state["user_name"]}_corpus_help_text'] = (
                prefix_text
            )
        elif (
            server_state[f'{st.session_state["user_name"]}_selected_corpus'] == "None"
        ):  # no corpus
            server_state[f'{st.session_state["user_name"]}_corpus_help_text'] = (
                prefix_text
            )
        else:  # metadata of selected corpus
            try:
                metadata = pd.read_csv(
                    f"""corpora/metadata_{server_state[f'{st.session_state["user_name"]}_selected_corpus']}.csv"""
                )
            except:  # it was deleted mid-text conversion
                metadata = pd.DataFrame(columns=["text_id"])
                metadata.to_csv(
                    f"""corpora/metadata_{server_state[f'{st.session_state["user_name"]}_selected_corpus']}.csv""",
                    index=False,
                )

                # recreate the directory
                if not (
                    os.path.isdir(
                        f"""corpora/{server_state[f'{st.session_state["user_name"]}_selected_corpus']}"""
                    )
                ):
                    os.makedirs(
                        f"""corpora/{server_state[f'{st.session_state["user_name"]}_selected_corpus']}"""
                    )

            try:
                metadata["file_path"] = [
                    x.split("/")[-1] for x in metadata["file_path"]
                ]  # show only filename
            except:
                st.error(
                    "You didn't upload a correctly formatted zip file. You should create a folder called EXACTLY `corpus` and put your files there. Then zip that file. To check, when you unzip the file it should produce a folder called `corpus`. If you want to include a metadata file, create one called EXACTLY `metadata.csv`, then highlight the CSV file and the corpus folder and zip them together. To check you did it properly, when you unzip the file, it should create one `metadata.csv` file and one `corpus` folder at the same level."
                )
            server_state[f'{st.session_state["user_name"]}_corpus_help_text'] = (
                f"""{prefix_text}\n\nMetadata of the selected corpus:\n{metadata.to_markdown(index=False)}"""
            )

        # determine their corpus
        if "user_list" not in st.session_state:
            st.session_state["user_list"] = pd.read_csv(
                "metadata/user_list.csv", keep_default_na=False
            )
            st.session_state["starting_corpus"] = (
                st.session_state["user_list"]
                .loc[lambda x: x["user"] == st.session_state["user_name"], "corpus"]
                .values[0]
            )

        server_state[f'{st.session_state["user_name"]}_selected_corpus'] = (
            st.sidebar.selectbox(
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
                index=(
                    (
                        ["None"]
                        + sorted(
                            [
                                x
                                for x in list(st.session_state["corpora_dict"].name)
                                if "temporary" not in x
                                or x == f"temporary_{st.session_state['db_name']}"
                            ]
                        )
                    ).index(st.session_state["starting_corpus"])
                    if f'{st.session_state["user_name"]}_selected_corpus'
                    not in server_state
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
                        server_state[f'{st.session_state["user_name"]}_selected_corpus']
                        if server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ]
                        is not None
                        else "None"
                    )
                ),
                help=server_state[f'{st.session_state["user_name"]}_corpus_help_text'],
            )
        )


def ui_advanced_model_params():
    "UI section for advanced model parameters"

    with st.sidebar.expander("Advanced model parameters"):
        # renaming new corpus
        with no_rerun:
            st.session_state["new_corpus_name"] = st.text_input(
                "Uploaded corpus name",
                value=(
                    f"temporary_{st.session_state['db_name']}"
                    if "new_corpus_name" not in st.session_state
                    else st.session_state["new_corpus_name"]
                ),
                help="The name of the new corpus you are processing. It must be able to be a SQL database name, so only lower case, no special characters, no spaces. Use underscores.",
            )

        # include history
        # reading in system prompt key
        if "system_prompt_key" not in st.session_state:
            st.session_state["system_prompt_key"] = pd.read_csv(
                "metadata/system_prompt_key.csv", keep_default_na=False
            )

            # starting system prompt
            st.session_state["starting_system_prompt"] = (
                st.session_state["system_prompt_key"]
                .loc[
                    lambda x: x["corpus"] == st.session_state["starting_corpus"],
                    "system_prompt",
                ]
                .values[0]
            )

        server_state[f'{st.session_state["user_name"]}_use_memory'] = st.checkbox(
            "Use chat memory?",
            value=(
                (
                    True
                    if st.session_state["system_prompt_key"]
                    .loc[
                        lambda x: x["corpus"]
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ],
                        "use_memory",
                    ]
                    .values[0]
                    == 1
                    else False
                )
                if f'{st.session_state["user_name"]}_use_memory' not in server_state
                else server_state[f'{st.session_state["user_name"]}_use_memory']
            ),
            help="Whether or not to have the model remember your chat history. If checked, you will be able to ask followup questions. If not checked, each query will be treated independently. The benefit of the latter is you can use the whole context length for RAG and not RAG + chat history, so you can increase your similarity top K.",
        )

        # similarity top k
        with no_rerun:
            if False:
                server_state[f'{st.session_state["user_name"]}_similarity_top_k'] = (
                    st.slider(
                        "Similarity top K",
                        min_value=1,
                        max_value=20,
                        step=1,
                        value=(
                            server_state["default_similarity_top_k"]
                            if f'{st.session_state["user_name"]}_similarity_top_k'
                            not in server_state
                            else server_state[
                                f'{st.session_state["user_name"]}_similarity_top_k'
                            ]
                        ),
                        # help="The number of contextual document chunks to retrieve for RAG.",
                        help=f"""The number of contextual document chunks to retrieve for RAG. `Similarity top K` * `Chunk size` must be less than your chosen LLM's context window, which is `{st.session_state["llm_dict"].loc[lambda x: x.name == server_state[f'{st.session_state["user_name"]}_selected_llm'], "context_window"].values[0]}`.""",
                    )
                )
            else:
                # cut top k in half if they're using memory
                divisor = (
                    2
                    if server_state[f'{st.session_state["user_name"]}_use_memory']
                    else 1
                )
                server_state[f'{st.session_state["user_name"]}_similarity_top_k'] = (
                    math.floor(
                        st.session_state["system_prompt_key"]
                        .loc[
                            lambda x: x["corpus"]
                            == server_state[
                                f'{st.session_state["user_name"]}_selected_corpus'
                            ],
                            "similarity_top_k",
                        ]
                        .values[0]
                        / divisor
                    )
                )

        # n_gpu layers
        st.session_state["n_gpu_layers"] = (
            100
            if "n_gpu_layers" not in st.session_state
            else st.session_state["n_gpu_layers"]
        )

        # temperature
        with no_rerun:
            server_state[f'{st.session_state["user_name"]}_temperature'] = st.slider(
                "Temperature",
                min_value=0,
                max_value=100,
                step=1,
                value=(
                    server_state["default_temperature"]
                    if f'{st.session_state["user_name"]}_temperature'
                    not in server_state
                    else server_state[f'{st.session_state["user_name"]}_temperature']
                ),
                help="How much leeway/creativity to give the model, 0 = least creativity, 100 = most creativity.",
            )

        # max_new tokens
        with no_rerun:
            server_state[f'{st.session_state["user_name"]}_max_new_tokens'] = st.slider(
                "Max new tokens",
                min_value=16,
                max_value=16000,
                step=8,
                value=(
                    server_state["default_max_new_tokens"]
                    if f'{st.session_state["user_name"]}_max_new_tokens'
                    not in server_state
                    else server_state[f'{st.session_state["user_name"]}_max_new_tokens']
                ),
                help="How long to limit the responses to (token ≈ word).",
            )

        # system prompt
        with no_rerun:
            try:
                server_state[f'{st.session_state["user_name"]}_system_prompt'] = (
                    st.session_state["starting_system_prompt"]
                    if f'{st.session_state["user_name"]}_system_prompt'
                    not in server_state
                    else (
                        st.session_state["system_prompt_key"]
                        .loc[
                            lambda x: x["corpus"]
                            == server_state[
                                f'{st.session_state["user_name"]}_selected_corpus'
                            ],
                            "system_prompt",
                        ]
                        .values[0]
                        if "temporary"
                        not in server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ]
                        else st.session_state["system_prompt_key"]
                        .loc[lambda x: x["corpus"] == "temporary", "system_prompt"]
                        .values[0]
                    )
                )
            except:  # a new named corpus, default to temporary system prompt
                server_state[f'{st.session_state["user_name"]}_system_prompt'] = (
                    st.session_state["system_prompt_key"]
                    .loc[lambda x: x["corpus"] == "temporary", "system_prompt"]
                    .values[0]
                )

        # params that affect the vector_db
        if False:
            st.markdown(
                "# Vector DB parameters",
                help="Changing these parameters will require remaking the vector database and require a bit longer to run. Push the `Reinitialize model and remake DB` button if you change one of these.",
            )

        # chunk overlap
        with no_rerun:
            if False:
                server_state[f'{st.session_state["user_name"]}_chunk_overlap'] = (
                    st.slider(
                        "Chunk overlap",
                        min_value=0,
                        max_value=1000,
                        step=1,
                        value=(
                            server_state["default_chunk_overlap"]
                            if f'{st.session_state["user_name"]}_chunk_overlap'
                            not in server_state
                            else server_state[
                                f'{st.session_state["user_name"]}_chunk_overlap'
                            ]
                        ),
                        help="How many tokens to overlap when chunking the documents.",
                    )
                )
            else:
                server_state[f'{st.session_state["user_name"]}_chunk_overlap'] = (
                    st.session_state["system_prompt_key"]
                    .loc[
                        lambda x: x["corpus"]
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ],
                        "chunk_overlap",
                    ]
                    .values[0]
                )

        # chunk size
        with no_rerun:
            if False:
                server_state[f'{st.session_state["user_name"]}_chunk_size'] = st.slider(
                    "Chunk size",
                    min_value=64,
                    max_value=6400,
                    step=8,
                    value=(
                        server_state["default_chunk_size"]
                        if f'{st.session_state["user_name"]}_chunk_size'
                        not in server_state
                        else server_state[f'{st.session_state["user_name"]}_chunk_size']
                    ),
                    help="How many tokens per chunk when chunking the documents.",
                )
            else:
                server_state[f'{st.session_state["user_name"]}_chunk_size'] = (
                    st.session_state["system_prompt_key"]
                    .loc[
                        lambda x: x["corpus"]
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ],
                        "chunk_size",
                    ]
                    .values[0]
                )

        # clear other models on reinitialize
        if False:
            st.session_state["clear_llms"] = st.checkbox(
                "Clear other LLMs on reinitialize",
                value=(
                    False
                    if "clear_llms" not in st.session_state
                    else st.session_state["clear_llms"]
                ),
                help="Whether or not to clear out other LLMs when selecting a new one. Check if you don't have enough VRAM to load multiple models simultaneously. NOTE: it will remove the LLM for all users.",
            )

            st.session_state["reinitialize_remake"] = st.button(
                "Reinitialize model and remake DB",
                help="Click if you make any changes to the vector DB parameters.",
            )
        else:
            st.session_state["clear_llms"] = False
            st.session_state["reinitialize_remake"] = False

    st.session_state["reinitialize"] = st.sidebar.button(
        "Reinitialize model",
        help="Click if you change the `Which LLM` or `Which corpus` options.",
    )

    # show error if chunk size * top k too large
    chunk_error = st.sidebar.empty()
    if (
        server_state[f'{st.session_state["user_name"]}_chunk_size']
        * server_state[f'{st.session_state["user_name"]}_similarity_top_k']
        > st.session_state["llm_dict"]
        .loc[
            lambda x: x.name
            == server_state[f'{st.session_state["user_name"]}_selected_llm'],
            "context_window",
        ]
        .values[0]
    ):
        chunk_error.error(
            f"""Chunk size ({server_state[f'{st.session_state["user_name"]}_chunk_size']}) * similarity top K ({server_state[f'{st.session_state["user_name"]}_similarity_top_k']}) = {server_state[f'{st.session_state["user_name"]}_chunk_size'] * server_state[f'{st.session_state["user_name"]}_similarity_top_k']} is larger than the context window ({st.session_state["llm_dict"].loc[lambda x: x.name == server_state[f'{st.session_state["user_name"]}_selected_llm'], "context_window"].values[0]}). Either decrease chunk size or lower similarity top K."""
        )
    else:
        chunk_error.empty()

    # set memory limit dynamically
    if f'{st.session_state["user_name"]}_memory_limit' not in server_state:
        # first boot is non-RAG, large memory
        update_server_state(
            f'{st.session_state["user_name"]}_memory_limit',
            st.session_state["llm_dict"]
            .loc[
                lambda x: x.name
                == server_state[f'{st.session_state["user_name"]}_selected_llm'],
                "context_window",
            ]
            .values[0]
            / 2,
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

        # reset parameters to defaults
        del server_state[f'{st.session_state["user_name"]}_selected_llm']
        del server_state[f'{st.session_state["user_name"]}_selected_corpus']
        del server_state[f'{st.session_state["user_name"]}_similarity_top_k']
        del server_state[f'{st.session_state["user_name"]}_temperature']
        del server_state[f'{st.session_state["user_name"]}_max_new_tokens']
        del server_state[f'{st.session_state["user_name"]}_memory_limit']
        del server_state[f'{st.session_state["user_name"]}_system_prompt']
        del server_state[f'{st.session_state["user_name"]}_chunk_overlap']
        del server_state[f'{st.session_state["user_name"]}_chunk_size']
        del server_state[f'{st.session_state["user_name"]}_own_urls']
        del server_state[f'{st.session_state["user_name"]}_own_urls_prefix']
        del server_state[f'{st.session_state["user_name"]}_own_urls_include_https']
        del server_state[f'{st.session_state["user_name"]}_gn_language']
        del server_state[f'{st.session_state["user_name"]}_gn_country']
        del server_state[f'{st.session_state["user_name"]}_gn_max_results']
        del server_state[f'{st.session_state["user_name"]}_gn_date_range']
        del server_state[f'{st.session_state["user_name"]}_gn_query']
        del server_state[f'{st.session_state["user_name"]}_gn_site_list']

        # do a database dump
        if (
            int(
                st.session_state["db_info"]
                .loc[lambda x: x.field == "dump_on_exit", "value"]
                .values[0]
            )
            == 1
        ):
            pg_dump(
                host=st.session_state["db_host"],
                port=st.session_state["db_port"],
                user=st.session_state["db_user"],
                password=st.session_state["db_password"],
                db_name=st.session_state["master_db_name"],
                filename="corpora/vector_db_dump.sql",
            )

        update_server_state(
            f'{st.session_state["user_name"]} messages', []
        )  # reset user's message history
        st.session_state["password_correct"] = False
        st.rerun()
        st.stop()

    # help contact
    st.sidebar.markdown(
        f"""*For questions on how to use this application or its methodology, please write [{server_state["author_name"]}](mailto:{server_state["author_email"]})*""",
        unsafe_allow_html=True,
    )


def populate_chat():
    # Display chat messages from history on app rerun
    st.session_state["message_box"] = st.empty()

    if f'{st.session_state["user_name"]} messages' in server_state:
        with st.session_state["message_box"].container():
            for index, message in enumerate(
                server_state[f'{st.session_state["user_name"]} messages']
            ):
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
                            help=message["content"]
                            .split("string:")[1]
                            .split("<br>")[0],
                        )


def import_chat():
    "UI element and logic for chat interface"

    if f'model_{st.session_state["db_name"]}' in server_state:
        # Initialize chat history
        if f'{st.session_state["user_name"]} messages' not in server_state:
            update_server_state(f'{st.session_state["user_name"]} messages', [])

        # populate the chat, only if not reinitialized/reprocess, in that case done elsewhere
        if not (
            f'model_{st.session_state["db_name"]}' not in server_state
            or st.session_state["reinitialize"]
            or st.session_state["reinitialize_remake"]
            or st.session_state["process_corpus_button"]
        ):
            populate_chat()

        # reset model's memory
        if st.session_state["reset_memory"]:
            if (
                server_state[f'model_{st.session_state["db_name"]}'].chat_engine
                is not None
            ):
                with no_rerun:
                    server_state[f'model_{st.session_state["db_name"]}'].chat_engine = (
                        None
                    )
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
                "Query '"
                + server_state[f'{st.session_state["user_name"]}_selected_llm']
                + "', not contextualized"
            )
        else:
            placeholder_text = (
                "Query '"
                + server_state[f'{st.session_state["user_name"]}_selected_llm']
                + "' contextualized on '"
                ""
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
                    server_state["in_use"]
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
                            update_server_state("in_use", False)
                            update_server_state(
                                "exec_queue", server_state["exec_queue"][1:]
                            )  # take the first person out of the queue
                            update_server_state("last_used", datetime.now())

                    t.markdown(
                        f'You are place {server_state["exec_queue"].index(st.session_state["user_name"])} of {len(server_state["exec_queue"]) - 1}'
                    )
                    time.sleep(1)
                t.empty()

            # lock the model while generating
            update_server_state("in_use", True)
            update_server_state("last_used", datetime.now())

            # generate response
            try:
                response = server_state[
                    f'model_{st.session_state["db_name"]}'
                ].gen_response(
                    prompt=server_state[f'{st.session_state["user_name"]} messages'][
                        -1
                    ]["content"][
                        : -(
                            len(
                                f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                            )
                        )
                    ],  # don't pass the time to the LLM ,
                    llm=server_state[
                        server_state[f'{st.session_state["user_name"]}_selected_llm']
                    ],
                    similarity_top_k=server_state[
                        f'{st.session_state["user_name"]}_similarity_top_k'
                    ],
                    temperature=server_state[
                        f'{st.session_state["user_name"]}_temperature'
                    ],
                    max_new_tokens=server_state[
                        f'{st.session_state["user_name"]}_max_new_tokens'
                    ],
                    use_chat_engine=server_state[
                        f'{st.session_state["user_name"]}_use_memory'
                    ],
                    reset_chat_engine=st.session_state["reset_chat_engine"],
                    memory_limit=(
                        server_state[f'{st.session_state["user_name"]}_memory_limit']
                        if server_state[f'{st.session_state["user_name"]}_use_memory']
                        else st.session_state["llm_dict"]
                        .loc[
                            lambda x: x.name
                            == server_state[
                                f'{st.session_state["user_name"]}_selected_llm'
                            ],
                            "context_window",
                        ]
                        .values[0]
                    ),
                    system_prompt=server_state[
                        f'{st.session_state["user_name"]}_system_prompt'
                    ],
                    context_prompt=(
                        ""
                        if server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ]
                        == "None"
                        or server_state[
                            f'{st.session_state["user_name"]}_selected_corpus'
                        ]
                        is None
                        else server_state["default_context_prompt"]
                    ),
                    streaming=True,
                    chat_mode="condense_plus_context",
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
                                if not (key in ["is_csv", "file_path"]):
                                    metadata_string += f"'{key}': '{value}'\n"

                            source_string += f"""# Source {counter}\n ### Metadata:\n ```{metadata_string}```\n ### Text:\n{response[j].split("| source text:")[1]}\n\n"""
                            counter += 1
                    else:
                        source_string = "NA"

                    # adding model information
                    source_string += "\n# Model parameters\n"
                    source_string += f"""```
Which LLM: {server_state[f'{st.session_state["user_name"]}_selected_llm']}
Which corpus: {server_state[f'{st.session_state["user_name"]}_selected_corpus']}
Similarity top K: {server_state[f'{st.session_state["user_name"]}_similarity_top_k']}
Temperature: {server_state[f'{st.session_state["user_name"]}_temperature']}
Max new tokens: {server_state[f'{st.session_state["user_name"]}_max_new_tokens']}
Context window: {st.session_state["llm_dict"].loc[lambda x: x.name == server_state[f'{st.session_state["user_name"]}_selected_llm'], "context_window"].values[0]}
Memory limit: {server_state[f'{st.session_state["user_name"]}_memory_limit']}
System prompt: {server_state[f'{st.session_state["user_name"]}_system_prompt']}
Context prompt: {"NA" if server_state[f'{st.session_state["user_name"]}_selected_corpus'] == "None" or server_state[f'{st.session_state["user_name"]}_selected_corpus'] is None else server_state['default_context_prompt']}
Chunk overlap: {server_state[f'{st.session_state["user_name"]}_chunk_overlap']}
Chunk size: {server_state[f'{st.session_state["user_name"]}_chunk_size']}
```
                    """
                    st.markdown(
                        "Sources: " + response_time,
                        unsafe_allow_html=True,
                        help=f"{source_string}",
                    )

                    # no memory warning
                    if not (
                        server_state[f'{st.session_state["user_name"]}_use_memory']
                    ):
                        st.warning(
                            "**Note**: For security reasons, the LLM will not remember the chat history. It will treat every query as a standalone question."
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
                    # + [{"role": "assistant", "content": response["response"].response}],
                    + [
                        {
                            "role": "assistant",
                            "content": st.session_state["assistant_answer"],
                        }
                    ],
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
            except:
                st.error(
                    "An error was encountered. Try reducing your similarity top K or chunk size."
                )
                # unlock the model
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )  # take out of the queue

    if "stop_displaying" in st.session_state:
        if st.session_state[
            "stop_displaying"
        ]:  # refresh to get rid of 'still thinking...' if it did more user:assistant:
            st.session_state["stop_displaying"] = False
            st.rerun()
