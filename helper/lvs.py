from local_vector_search.local_vector_search import local_vs
from nlp_pipeline.nlp_pipeline import nlp_processor
import os
import pandas as pd
import polars as pl
import shutil
import streamlit as st
import time
import zipfile

from helper.sidebar import make_new_chat


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
    with st.spinner("Setting up...", show_time=True):
        temp_directory = f'corpora/tmp_helper_{st.session_state["user_name"]}/'
        corpora_path = "corpora"

        if st.session_state["new_corpus_name"] == "Workspace":
            corpus_name = f'Workspace {st.session_state["user_name"]}'
        else:
            corpus_name = st.session_state["new_corpus_name"].copy()

        # make temporary directory to handle files
        if not os.path.exists(f"{temp_directory}"):
            os.makedirs(f"{temp_directory}")
        else:  # clear it out
            shutil.rmtree(f"{temp_directory}")
            os.makedirs(f"{temp_directory}")

        # if corpus name temporary, delete everything in the temporary files
        if corpus_name == f'Workspace {st.session_state["new_corpus_name"]}':
            if os.path.exists(f"{corpora_path}/{corpus_name}/"):
                shutil.rmtree(f"{corpora_path}/{corpus_name}/")
            if os.path.exists(f"{corpora_path}/metadata_{corpus_name}.csv"):
                os.remove(f"{corpora_path}/metadata_{corpus_name}.csv")

        # if this corpus already exists, overwrite it
        if os.path.exists(f"{corpora_path}/{corpus_name}"):
            shutil.rmtree(f"{corpora_path}/{corpus_name}/")

            try:
                os.remove(f"{corpora_path}/metadata_{corpus_name}.csv")
            except:
                pass

            try:
                os.remove(f"{corpora_path}/embeddings_{corpus_name}.parquet")
            except:
                pass

        # write the uploaded file
        with open(
            f"""{temp_directory}tmp.{st.session_state["uploaded_file"].name.split('.')[-1]}""",
            "wb",
        ) as new_file:
            new_file.write(st.session_state["uploaded_file"].getbuffer())
            new_file.close()

        ### process the uploaded file
        # convert documents to text
        os.makedirs(f"{corpora_path}/{corpus_name}/tmp")

        processor = nlp_processor(
            data_path=f"{corpora_path}/{corpus_name}/tmp",
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
                with st.spinner(f"Downloading file {i+1}/{len(metadata)} (step 1 of 3"):
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
            f"{corpora_path}/{corpus_name}/zip_output/",
        )

        # case 3: uploaded a zip file with only documents
        zip_files = [
            _
            for _ in os.listdir(f"{corpora_path}/{corpus_name}/zip_output/")
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
                    ]
                )
                and "._" not in _
            )
        ]

        print(zip_files)

        if "metadata.csv" not in zip_files:
            # create metadata
            metadata = pd.DataFrame(
                {
                    "text_id": list(range(1, len(zip_files) + 1)),
                    "local_raw_filepath": [
                        f"{corpora_path}/{corpus_name}/zip_output/{_}"
                        for _ in zip_files
                    ],
                },
            )

        # case 4: uploaded a zip file with metadata + documents
        else:
            metadata = pd.read_csv(
                f"{corpora_path}/{corpus_name}/zip_output/metadata.csv"
            )
            metadata["text_id"] = list(range(1, len(metadata) + 1))
            metadata["local_raw_filepath"] = [
                f"{corpora_path}/{corpus_name}/zip_output/{_}"
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
    processor.metadata.drop(
        [
            "local_raw_filepath",
            "local_txt_filepath",
            "detected_language",
            "web_filepath",
        ],
        axis=1,
    ).to_csv(f"{corpora_path}/metadata_{corpus_name}.csv", index=False)

    # move .txt files to appropriate place and clean up
    for filename in os.listdir(f"{corpora_path}/{corpus_name}/tmp/txt_files/"):
        shutil.move(
            f"{corpora_path}/{corpus_name}/tmp/txt_files/{filename}",
            f"{corpora_path}/{corpus_name}/{filename}",
        )

    # remove tmp directory
    shutil.rmtree(f"{corpora_path}/{corpus_name}/tmp/")

    # remove zip directory
    try:
        shutil.rmtree(f"{corpora_path}/{corpus_name}/zip_output/")
    except:
        pass

    # remove original file
    shutil.rmtree(temp_directory)

    # embed documents
    vs = local_vs(
        metadata_path=f"{corpora_path}/metadata_{corpus_name}.csv",
        files_path=f"{corpora_path}/{corpus_name}/",
        model="all-MiniLM-L6-v2",
        tokenizer_name="meta-llama/Llama-2-7b-hf",
        clean_text_function=None,
        include_metadata=False,
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

    vs.embeddings_df = final_embeddings
    vs.embeddings_df.write_parquet(f"{corpora_path}/embeddings_{corpus_name}.parquet")

    # update the corpus list csv
    tmp_corpora_list = pd.DataFrame(
        {
            "name": corpus_name,
            "text_path": f"{corpora_path}/{corpus_name}/",
            "metadata_path": f"{corpora_path}/metadata_{corpus_name}.csv",
            "system_prompt": st.session_state["system_prompt"],
        },
        index=[0],
    )

    st.session_state["corpora_list"] = pd.concat(
        [st.session_state["corpora_list"], tmp_corpora_list], ignore_index=True
    )
    st.session_state["corpora_list"].to_csv("metadata/corpora_list.csv", index=False)

    # clean up and initiating new chat with the corpus loaded
    with st.spinner(
        "New chat initializing for your corpus in 5 seconds", show_time=True
    ):
        st.info("Corpus successfully embedded, ready for querying!")
        time.sleep(5)
        st.session_state["selected_corpus"] = st.session_state["new_corpus_name"]
        make_new_chat()
