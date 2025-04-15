from local_vector_search.local_vector_search import local_vs
from local_vector_search.misc import pickle_save
from nlp_pipeline.nlp_pipeline import nlp_processor
import os
import pandas as pd
import polars as pl
import shutil
import streamlit as st
from streamlit_server_state import no_rerun, server_state, server_state_lock
import time
import zipfile


cite_source_instruction = """\n\nAt the end of any information that you support from the excerpts, place the following text: <span class="tooltip superscript-link">†<span class="tooltiptext">chunk_id</span></span>, where you replace 'chunk_id' with the chunk id number of the excerpt you are referencing. Repeat the whole tag if you are referencing multiple chunks in one sentence."""


def update_server_state(key, value):
    "update the server state variable"
    with no_rerun:
        with server_state_lock[key]:
            server_state[key] = value


def save_user_settings(selected_chat_name=None, display_metadata_overwrite=True):
    if not (os.path.isdir("metadata/user_settings/")):
        os.makedirs("metadata/user_settings/")

    # update values with the current ones
    if selected_chat_name is None:
        try:
            st.session_state["user_settings"]["selected_chat_name"] = st.session_state[
                "selected_chat_name"
            ]
        except:
            pass
    else:
        st.session_state["user_settings"]["selected_chat_name"] = selected_chat_name

    st.session_state["user_settings"]["cite_sources"] = st.session_state["cite_sources"]
    st.session_state["user_settings"]["selected_llm"] = st.session_state["selected_llm"]
    try:
        st.session_state["user_settings"]["selected_corpus"] = st.session_state[
            "selected_corpus"
        ]
    except:
        pass
    st.session_state["user_settings"]["temperature_string"] = st.session_state[
        "temperature_string"
    ]
    st.session_state["user_settings"]["system_prompt"] = st.session_state[
        "system_prompt"
    ]
    if (
        display_metadata_overwrite
    ):  # only overwrite if want to, not for delete corpus or process new corpus with same name
        try:  # won't work if they're changing from no corpus
            st.session_state["user_settings"]["display_metadata"][
                st.session_state["selected_corpus_realname"]
            ] = st.session_state["display_metadata"]
        except:
            pass

    # save user settings
    pickle_save(
        st.session_state["user_settings"],
        f'metadata/user_settings/{st.session_state["user_name"]}.pickle',
    )

    # save chat history
    pickle_save(
        st.session_state["chat_history"],
        f"""metadata/chat_histories/{st.session_state["user_name"]}_chats.pickle""",
    )


def make_new_chat(display_metadata_overwrite=True):
    # don't want to allow multiple new chats
    try:
        last_num = max(
            [
                v["chat_name"]
                for k, v in st.session_state["chat_history"].items()
                if "New chat" in v["chat_name"]
            ]
        ).split(" ")[-1]
        if last_num == "chat":
            new_chat_name = "New chat 2"
        else:
            new_chat_name = "New chat " + str(int(last_num) + 1)
    except:
        new_chat_name = "New chat"

    st.session_state["selected_chat_id"] = st.session_state["latest_chat_id"] + 1
    st.session_state["latest_chat_id"] += 1
    st.session_state["chat_history"][st.session_state["selected_chat_id"]] = {}
    if "cite_sources" not in st.session_state:
        st.session_state["cite_sources"] = False
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "messages"
    ] = [
        {
            "role": "system",
            "content": st.session_state["system_prompt"]
            + (cite_source_instruction if st.session_state["cite_sources"] else ""),
        }
    ]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]]["times"] = [
        None
    ]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "reasoning"
    ] = [""]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "chat_name"
    ] = new_chat_name
    st.session_state["chat_history"][st.session_state["selected_chat_id"]]["corpus"] = [
        ""
    ]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "chunk_ids"
    ] = [[]]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "selected_llm"
    ] = [""]
    st.session_state["chat_history"][st.session_state["selected_chat_id"]][
        "model_style"
    ] = [""]

    # change selected chat
    try:  # will fail if it's the users first load
        save_user_settings(
            selected_chat_name=st.session_state["chat_history"][
                st.session_state["selected_chat_id"]
            ]["chat_name"],
            display_metadata_overwrite=display_metadata_overwrite,
        )
    except:
        pass

    del st.session_state["initialized"]
    try:
        del st.session_state["selected_chat_name"]
    except:
        pass


# helper unzip function
def unzip_file(zip_path, output_dir="zip_output"):
    """
    Unzip a file and extract all contents to a specified output directory.

    Args:
    zip_path (str): Path to the zip file
    output_dir (str, optional): Directory to extract files to. Defaults to 'zip_output'.

    Returns:
    list: List of extracted file paths
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Open the zip file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Iterate through all files in the zip
        for file in zip_ref.namelist():
            # Remove any leading directory separators
            file = file.lstrip("/")

            # Skip directories and empty strings
            if not file or file.endswith("/"):
                continue

            # Extract file content
            source = zip_ref.open(file)

            # Create full output path, ignoring original directory structure
            filename = os.path.basename(file)

            # Handle filename conflicts by adding a number
            base, ext = os.path.splitext(filename)
            counter = 1
            output_filename = filename
            while os.path.exists(os.path.join(output_dir, output_filename)):
                output_filename = f"{base}_{counter}{ext}"
                counter += 1

            # Full path for the output file
            output_path = os.path.join(output_dir, output_filename)

            # Write the file
            with open(output_path, "wb") as target:
                shutil.copyfileobj(source, target)


def process_corpus():
    "process a corpus into text and create the vector db"
    with st.spinner("Processing corpus..."):
        # clear out the message history
        st.session_state["message_box"].empty()

        if st.session_state["new_corpus_name"] != "Workspace":
            new_name = st.session_state["new_corpus_name"]
        else:
            new_name = f'Workspace {st.session_state["user_name"]}'

        with st.spinner("Setting up...", show_time=True):
            temp_directory = f'corpora/tmp_helper_{st.session_state["user_name"]}/'

            # make temporary directory to handle files
            if not os.path.exists(f"{temp_directory}"):
                os.makedirs(f"{temp_directory}")
            else:  # clear it out
                shutil.rmtree(f"{temp_directory}")
                os.makedirs(f"{temp_directory}")

            # if corpus name temporary, delete everything in the temporary files
            if new_name == f'Workspace {st.session_state["new_corpus_name"]}':
                if os.path.exists(f'{st.session_state["corpora_path"]}/{new_name}/'):
                    shutil.rmtree(f'{st.session_state["corpora_path"]}/{new_name}/')
                if os.path.exists(
                    f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv'
                ):
                    os.remove(
                        f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv'
                    )

            # if this corpus already exists, overwrite it
            if os.path.exists(f'{st.session_state["corpora_path"]}/{new_name}'):
                shutil.rmtree(f'{st.session_state["corpora_path"]}/{new_name}/')

                try:
                    os.remove(
                        f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv'
                    )
                except:
                    pass

                try:
                    os.remove(
                        f'{st.session_state["corpora_path"]}/embeddings_{new_name}.parquet'
                    )
                except:
                    pass

            # write the uploaded file
            try:
                with open(
                    f"""{temp_directory}tmp.{st.session_state["uploaded_file"].name.split('.')[-1]}""",
                    "wb",
                ) as new_file:
                    new_file.write(st.session_state["uploaded_file"].getbuffer())
                    new_file.close()
            except:
                st.error("Are you sure you uploaded a file?")

            ### process the uploaded file
            # convert documents to text
            os.makedirs(f'{st.session_state["corpora_path"]}/{new_name}/tmp')

            processor = nlp_processor(
                data_path=f'{st.session_state["corpora_path"]}/{new_name}/tmp',
                metadata_addt_column_names=[],
            )

        # case 1: uploaded a metadata.csv
        if st.session_state["uploaded_file"].name == "metadata.csv":
            metadata = pd.read_csv(
                f"""{temp_directory}/tmp.{st.session_state["uploaded_file"].name.split('.')[-1]}"""
            )

            # add text_id if not there
            if "text_id" not in metadata.columns:
                metadata["text_id"] = list(range(1, len(metadata) + 1))

            for col in metadata.columns:
                processor.metadata[col] = metadata[col]

            # download the files
            progress_message = st.empty()
            for i in range(len(metadata)):
                with progress_message.container():
                    with st.spinner(
                        f"Downloading file {i+1}/{len(metadata)} (step 1 of 3"
                    ):
                        processor.download_text_id(processor.metadata["text_id"][i])

        # case 2: uploaded only a single document
        elif st.session_state["uploaded_file"].name.split(".")[1] != "zip":
            # create metadata
            metadata = pd.DataFrame(
                {
                    "text_id": 1,
                    "local_raw_filepath": f"""{temp_directory}/tmp.{st.session_state["uploaded_file"].name.split('.')[-1]}""",
                },
                index=[0],
            )

            # sync the object's metadata to the local file
            for col in metadata.columns:
                processor.metadata[col] = metadata[col]

        # zip cases
        elif st.session_state["uploaded_file"].name.split(".")[1] == "zip":
            unzip_file(
                f"""{temp_directory}/tmp.{st.session_state["uploaded_file"].name.split('.')[-1]}""",
                f'{st.session_state["corpora_path"]}/{new_name}/zip_output/',
            )

            # case 3: uploaded a zip file with only documents
            zip_files = [
                _
                for _ in os.listdir(
                    f'{st.session_state["corpora_path"]}/{new_name}/zip_output/'
                )
                if (
                    any(
                        sub in _
                        for sub in [
                            ".docx",
                            ".doc",
                            ".pdf",
                            ".txt",
                            ".mp3",
                            ".mp4",
                            ".wav",
                            ".csv",
                            ".xlsx",
                            ".xls",
                            ".pptx",
                        ]
                    )
                    and "._" not in _
                )
            ]

            if "metadata.csv" not in zip_files:
                # create metadata
                metadata = pd.DataFrame(
                    {
                        "text_id": list(range(1, len(zip_files) + 1)),
                        "local_raw_filepath": [
                            f'{st.session_state["corpora_path"]}/{new_name}/zip_output/{_}'
                            for _ in zip_files
                        ],
                    },
                )

            # case 4: uploaded a zip file with metadata + documents
            else:
                metadata = pd.read_csv(
                    f'{st.session_state["corpora_path"]}/{new_name}/zip_output/metadata.csv'
                )
                metadata["text_id"] = list(range(1, len(metadata) + 1))
                metadata["local_raw_filepath"] = [
                    f'{st.session_state["corpora_path"]}/{new_name}/zip_output/{_}'
                    for _ in metadata["filepath"]
                ]

            for col in metadata.columns:
                processor.metadata[col] = metadata[col]

        # convert to text
        progress_message = st.empty()
        for i in range(len(metadata)):
            with progress_message.container():
                with st.spinner(
                    f"Converting files to text: {i+1}/{len(metadata)} (step 2 of 3)"
                ):
                    processor.convert_to_text(processor.metadata["text_id"][i])

        # write out metadata file
        processor.metadata["filepath"] = [
            f"{str(i)}.txt" for i in processor.metadata["text_id"]
        ]

        # add a new column for original file name
        try:
            # only do if there is no other metadata
            if not (
                set(processor.metadata.columns)
                - {
                    "text_id",
                    "filepath",
                    "vector_weight",
                    "local_raw_filepath",
                    "local_txt_filepath",
                    "detected_language",
                    "web_filepath",
                }
            ):
                processor.metadata["filename"] = [
                    _.split("/")[-1] for _ in processor.metadata["local_raw_filepath"]
                ]
        except:
            pass

        processor.metadata.drop(
            [
                "local_raw_filepath",
                "local_txt_filepath",
                "detected_language",
                "web_filepath",
            ],
            axis=1,
        ).to_csv(
            f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv',
            index=False,
        )

        # move .txt files to appropriate place and clean up
        for filename in os.listdir(
            f'{st.session_state["corpora_path"]}/{new_name}/tmp/txt_files/'
        ):
            shutil.move(
                f'{st.session_state["corpora_path"]}/{new_name}/tmp/txt_files/{filename}',
                f'{st.session_state["corpora_path"]}/{new_name}/{filename}',
            )

        # remove tmp directory
        shutil.rmtree(f'{st.session_state["corpora_path"]}/{new_name}/tmp/')

        # remove zip directory
        try:
            shutil.rmtree(f'{st.session_state["corpora_path"]}/{new_name}/zip_output/')
        except:
            pass

        # remove original file
        shutil.rmtree(temp_directory)

        # embed documents
        vs = local_vs(
            metadata_path=f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv',
            files_path=f'{st.session_state["corpora_path"]}/{new_name}/',
            model="all-MiniLM-L6-v2",
            tokenizer_name="meta-llama/Llama-2-7b-hf",
            clean_text_function=None,
            include_metadata=False,
            include_chunk_id_metadata_string=True,
        )

        progress_message = st.empty()
        for i in range(len(metadata)):
            with progress_message.container():
                with st.spinner(
                    f"Embedding documents: {i+1}/{len(metadata)} (step 3 of 3)"
                ):
                    embeddings = vs.embed_docs(
                        chunk_size=int(
                            st.session_state["settings"]
                            .loc[lambda x: x["field"] == "chunk_size", "value"]
                            .values[0]
                        ),
                        chunk_overlap=int(
                            st.session_state["settings"]
                            .loc[lambda x: x["field"] == "chunk_overlap", "value"]
                            .values[0]
                        ),
                        embeddings_path=None,
                        quiet=True,
                        text_ids=[metadata.loc[i, "text_id"]],
                    )

                    if i == 0:
                        final_embeddings = embeddings
                    else:
                        final_embeddings = pl.concat([final_embeddings, embeddings])

        # renaming chunk ids in metadata_string
        final_embeddings = final_embeddings.with_columns(
            [
                pl.format("chunk id: {}", pl.arange(0, final_embeddings.height)).alias(
                    "row_num"
                ),
                pl.col("metadata_string")
                .str.replace(r"chunk id: \d+", "row_placeholder")
                .alias("temp_meta"),
            ]
        ).with_columns(
            [
                pl.col("temp_meta")
                .str.replace("row_placeholder", pl.col("row_num").cast(pl.Utf8))
                .alias("metadata_string")
            ]
        )

        # remove duplicate chunk ids
        final_embeddings = final_embeddings.with_columns(
            pl.arange(0, final_embeddings.height).alias("chunk_id")
        )
        vs.embeddings_df = final_embeddings
        vs.embeddings_df.write_parquet(
            f'{st.session_state["corpora_path"]}/embeddings_{new_name}.parquet'
        )

        # update the corpus list csv
        if st.session_state["use_default_system_prompts"]:
            sys_prompt = (
                st.session_state["settings"]
                .loc[lambda x: x["field"] == "default_corpus_system_prompt", "value"]
                .values[0]
            )
        else:
            sys_prompt = st.session_state["system_prompt"]

        tmp_corpora_list = pd.DataFrame(
            {
                "name": new_name,
                "text_path": f'{st.session_state["corpora_path"]}/{new_name}/',
                "metadata_path": f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv',
                "user_list": ",".join(st.session_state["visible_corpus_names"]),
                "system_prompt": sys_prompt,
                "private": 1 if st.session_state["private_corpus"] else 0,
            },
            index=[0],
        )

        st.session_state["corpora_list"] = pd.concat(
            [
                st.session_state["corpora_list"].loc[lambda x: x["name"] != new_name],
                tmp_corpora_list,
            ],
            ignore_index=True,
        )
        st.session_state["corpora_list"].to_csv(
            "metadata/corpora_list.csv", index=False
        )

        # add the corpus to the server dict
        with no_rerun:
            with server_state_lock["lvs_corpora"]:
                server_state["lvs_corpora"][new_name] = local_vs(
                    metadata_path=f'{st.session_state["corpora_path"]}/metadata_{new_name}.csv',
                    embeddings_path=f'{st.session_state["corpora_path"]}/embeddings_{new_name}.parquet',
                )

    # clean up and initiating new chat with the corpus loaded
    with st.spinner(
        "New chat initializing for your corpus in 5 seconds", show_time=True
    ):
        st.info("Corpus successfully embedded, ready for querying!")
        time.sleep(5)
        del st.session_state["selected_corpus"]
        st.session_state["user_settings"]["selected_corpus"] = st.session_state[
            "new_corpus_name"
        ]
        # delete an existing corpus with this metadata
        try:
            if st.session_state["new_corpus_name"] == "Workspace":
                real_name = f"Workspace {st.session_state['user_name']}"
            else:
                real_name = st.session_state["new_corpus_name"]
            del st.session_state["user_settings"]["display_metadata"][real_name]
        except:
            pass
        del st.session_state["new_corpus_name"]
        make_new_chat(display_metadata_overwrite=False)


def load_lvs_corpora():
    if "lvs_corpora" not in server_state:
        with st.spinner("Initial boot..."):
            lvs_corpora_dict = {}

            for file in os.listdir(st.session_state["corpora_path"]):
                if "embeddings" in file:
                    lvs_corpora_dict[
                        file.split("embeddings_")[1].split(".parquet")[0]
                    ] = local_vs(
                        metadata_path=f'{st.session_state["corpora_path"]}/{file.replace(".parquet", ".csv").replace("embeddings", "metadata")}',
                        embeddings_path=f'{st.session_state["corpora_path"]}/{file}',
                    )

            update_server_state("lvs_corpora", lvs_corpora_dict)
