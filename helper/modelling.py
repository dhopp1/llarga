import gc
import os
import sys

from local_rag_llm import local_llm
from local_rag_llm.model_setup import instantiate_llm
import streamlit as st
from streamlit_server_state import server_state

from helper.own_corpus import (
    check_db_exists,
    check_table_exists,
    process_corpus,
    transfer_db,
)
from helper.progress_bar import Logger
from helper.ui import populate_chat
from helper.user_management import (
    clear_models,
    update_server_state,
)


def set_static_model_params():
    st.session_state["paragraph_separator"] = "\n\n\n"
    st.session_state["separator"] = " "
    st.session_state["use_chat_engine"] = True
    st.session_state["reset_chat_engine"] = False


def determine_rerun_reinitialize():
    "determine values of 'rerun_populate_db', 'clear_database', 'reinitialized_db'"
    if f'{st.session_state["user_name"]}_rerun_populate_db' not in server_state:
        update_server_state(f'{st.session_state["user_name"]}_rerun_populate_db', False)
    if f'{st.session_state["user_name"]}_clear_database' not in server_state:
        update_server_state(f'{st.session_state["user_name"]}_clear_database', False)

    # reinitialize the vector db for simultaneous access initially
    if f'{st.session_state["user_name"]}_reinitialized_db' not in server_state:
        update_server_state(f'{st.session_state["user_name"]}_reinitialized_db', False)
    else:
        update_server_state(f'{st.session_state["user_name"]}_reinitialized_db', True)

    if not (server_state[f'{st.session_state["user_name"]}_reinitialized_db']):
        # only run if database exists
        if check_db_exists(
            user=st.session_state["db_info"].loc[0, "user"],
            password=st.session_state["db_info"].loc[0, "password"],
            db_name=st.session_state["master_db_name"],
        ):
            transfer_db(
                user=st.session_state["db_info"].loc[0, "user"],
                password=st.session_state["db_info"].loc[0, "password"],
                source_db=st.session_state["master_db_name"],
                target_db=st.session_state["db_name"],
            )


def initialize_llm():
    "initialize an LLM"
    if f'{st.session_state["user_name"]}_selected_llm' in server_state:
        llm_name = server_state[f'{st.session_state["user_name"]}_selected_llm']
    else:
        llm_name = st.session_state["llm_dict"].loc[0, "name"].values[0]

    if llm_name not in server_state:
        try:
            update_server_state(
                llm_name,
                instantiate_llm(
                    llm_path=st.session_state["llm_dict"]
                    .loc[
                        lambda x: x.name
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_llm'
                        ],
                        "llm_path",
                    ]
                    .values[0],
                    n_gpu_layers=100,
                    context_window=st.session_state["llm_dict"]
                    .loc[
                        lambda x: x.name
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_llm'
                        ],
                        "context_window",
                    ]
                    .values[0],
                ),
            )
        except:
            st.error("Not enough memory to load this model.")


def initialize_rag_pipeline(
    which_corpus_local=None,
    chunk_overlap=200,
    chunk_size=512,
    paragraph_separator="\n\n\n",
    separator=" ",
    rerun_populate_db=False,
    clear_database_local=False,
    corpora_dict=None,
    db_name="vector_db",
    db_info=None,
):
    "initialize a session's RAG pipeline"

    text_path = (
        corpora_dict.loc[lambda x: x.name == which_corpus_local, "text_path"].values[0]
        if which_corpus_local is not None
        else None
    )

    # remove any non-text files in text path on Mac
    if text_path is not None:
        files = os.listdir(text_path)
        for item in files:
            if not (item.endswith(".txt") or item.endswith(".csv")):
                os.remove(os.path.join(text_path, item))

    metadata_path = (
        corpora_dict.loc[
            lambda x: x.name == which_corpus_local, "metadata_path"
        ].values[0]
        if which_corpus_local is not None
        else None
    )

    user_rag_pipeline = local_llm.local_llm(
        text_path=text_path,
        metadata_path=metadata_path,
        hf_token=os.getenv("HF_TOKEN"),
    )

    if which_corpus_local is not None:
        if rerun_populate_db:
            clear_table = True
        else:
            clear_table = False

        user_rag_pipeline.setup_db(
            db_name=db_name,
            user=db_info.loc[0, "user"],
            password=db_info.loc[0, "password"],
            table_name=which_corpus_local,
            clear_database=clear_database_local,
            clear_table=clear_table,
        )

        # check if table exists
        with user_rag_pipeline.db_connection.cursor() as c:
            c.execute(
                f"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='data_{which_corpus_local}')"
            )
            table_exists = c.fetchone()[0]

        if rerun_populate_db or not (table_exists):
            user_rag_pipeline.populate_db(
                chunk_overlap=chunk_overlap,
                chunk_size=chunk_size,
                paragraph_separator=paragraph_separator,
                separator=separator,
                quiet=False,
            )
    return user_rag_pipeline, which_corpus_local


def load_rag_pipeline():
    "load the user-specific RAG pipeline in the application"
    if (
        f'model_{st.session_state["db_name"]}' not in server_state
        or st.session_state["reinitialize"]
        or st.session_state["reinitialize_remake"]
        or st.session_state["process_corpus_button"]
    ):
        clear_models()

        # update the memory limit
        update_server_state(
            f'{st.session_state["user_name"]}_memory_limit',
            int(
                (
                    1
                    - server_state[f'{st.session_state["user_name"]}_similarity_top_k']
                    * server_state[f'{st.session_state["user_name"]}_chunk_size']
                    / st.session_state["llm_dict"]
                    .loc[
                        lambda x: x.name
                        == server_state[
                            f'{st.session_state["user_name"]}_selected_llm'
                        ],
                        "context_window",
                    ]
                    .values[0]
                )
                * st.session_state["llm_dict"]
                .loc[
                    lambda x: x.name
                    == server_state[f'{st.session_state["user_name"]}_selected_llm'],
                    "context_window",
                ]
                .values[0]
                - 200
            ),
        )

        # hid messages so you can see the initializer
        if "message_box" in st.session_state:
            st.session_state["message_box"].empty()

        if st.session_state["process_corpus_button"]:
            if not (
                (
                    st.session_state["new_corpus_name"]
                    == f"temporary_{st.session_state['db_name']}"
                )
                or (
                    st.session_state["new_corpus_name"]
                    not in list(st.session_state["corpora_dict"].name.values)
                )
            ):
                st.error("A corpus with this name already exists, choose another one.")
            else:
                with st.spinner("Processing corpus..."):
                    old_stdout = sys.stdout
                    sys.stdout = Logger(st.progress(0), st.empty())
                    st.session_state["corpora_dict"] = process_corpus(
                        user_name=st.session_state["db_name"],
                        corpus_name=st.session_state["new_corpus_name"],
                        own_urls=st.session_state["own_urls"],
                        uploaded_document=st.session_state["uploaded_file"],
                        passed_google_news=False
                        if server_state[f'{st.session_state["user_name"]}_gn_query']
                        == ""
                        else True,
                    )

                update_server_state(
                    f'{st.session_state["user_name"]}_selected_corpus',
                    st.session_state["new_corpus_name"],
                )

        clear_models()

        with st.spinner("Initializing..."):
            # whether or not to remake the vector DB
            if (
                st.session_state["reinitialize_remake"]
                or st.session_state["process_corpus_button"]
            ):
                st.session_state["local_rerun_populate_db"] = True
                st.session_state["clear_database_local"] = server_state[
                    f'{st.session_state["user_name"]}_clear_database'
                ]
            else:
                st.session_state["local_rerun_populate_db"] = server_state[
                    f'{st.session_state["user_name"]}_rerun_populate_db'
                ]
                st.session_state["clear_database_local"] = server_state[
                    f'{st.session_state["user_name"]}_clear_database'
                ]

            def model_initialization():
                (
                    model,
                    which_corpus,
                ) = initialize_rag_pipeline(
                    which_corpus_local=None
                    if server_state[f'{st.session_state["user_name"]}_selected_corpus']
                    == "None"
                    else server_state[
                        f'{st.session_state["user_name"]}_selected_corpus'
                    ],
                    chunk_overlap=server_state[
                        f'{st.session_state["user_name"]}_chunk_overlap'
                    ],
                    chunk_size=server_state[
                        f'{st.session_state["user_name"]}_chunk_size'
                    ],
                    paragraph_separator=st.session_state["paragraph_separator"],
                    separator=st.session_state["separator"],
                    rerun_populate_db=st.session_state["local_rerun_populate_db"],
                    clear_database_local=st.session_state["clear_database_local"],
                    corpora_dict=st.session_state["corpora_dict"],
                    db_name=st.session_state["db_name"],
                    db_info=st.session_state["db_info"],
                )
                update_server_state(f'model_{st.session_state["db_name"]}', model)
                update_server_state(
                    f'{st.session_state["db_name"]}_which_corpus', which_corpus
                )
                del model
                gc.collect()

            model_initialization()

            # clear the progress bar
            if (
                server_state[f'{st.session_state["user_name"]}_rerun_populate_db']
                or st.session_state["process_corpus_button"]
            ):
                try:
                    sys.stdout = sys.stdout.clear()
                    sys.stdout = old_stdout
                except:
                    pass

            # copy the new table to master vector_db if it's not already there
            if not (
                check_table_exists(
                    user=st.session_state["db_info"].loc[0, "user"],
                    password=st.session_state["db_info"].loc[0, "password"],
                    db_name=st.session_state["master_db_name"],
                    table_name="data_"
                    + server_state[f'{st.session_state["db_name"]}_which_corpus']
                    if server_state[f'{st.session_state["db_name"]}_which_corpus']
                    is not None
                    else "None",
                )
            ):
                # close the model connection to not have simulataneous ones
                clear_models()

                # transfer the db
                transfer_db(
                    user=st.session_state["db_info"].loc[0, "user"],
                    password=st.session_state["db_info"].loc[0, "password"],
                    source_db=st.session_state["db_name"],
                    target_db=st.session_state["master_db_name"],
                )

                # reinitialize the model
                st.session_state["local_rerun_populate_db"] = False # don't repopulate the DB again
                model_initialization()

            # repopulate the chat
            populate_chat()
            st.info("Model successfully initialized!")
