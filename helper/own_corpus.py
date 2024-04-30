import os
import types
import shutil
from nlp_pipeline.nlp_pipeline import nlp_processor
import pandas as pd
from zipfile import ZipFile
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import streamlit as st
from streamlit_server_state import server_state

from helper.agents import (
    available_countries,
    available_languages,
    gen_google_news,
    gen_google_search,
)


# set these to the install locations if on Windows
windows_tesseract_path = None
windows_poppler_path = None


def transfer_db(host, port, user, password, source_db, target_db):
    "drop target db and replace it with source db"
    # establish connection
    conn = psycopg2.connect(
        f"host={host} port={port} dbname=postgres user={user} password={password}"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # drop target database if it already exists
    cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(target_db)))
    conn.commit()

    # Create new target database from source database
    cur.execute(
        sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(target_db), sql.Identifier(source_db)
        )
    )
    conn.commit()

    cur.close()
    conn.close()

    # drop all temporary tables from target db
    conn = psycopg2.connect(
        f"host={host} port={port} dbname={target_db} user={user} password={password}"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(
        sql.SQL(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
    )
    tables = cur.fetchall()
    tables = [x[0] for x in tables if "temporary" in x[0]]

    if len(tables) > 0:
        for drop in tables:
            cur.execute(sql.SQL(f"DROP TABLE {drop}"))

    cur.close()
    conn.close()


def check_db_exists(host, port, user, password, db_name):
    "check if a database exists"
    conn = psycopg2.connect(
        f"host={host} port={port} dbname=postgres user={user} password={password}"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(sql.SQL("SELECT datname FROM pg_database WHERE datistemplate = false;"))
    dbs = cur.fetchall()

    result = db_name in [x[0] for x in dbs]

    cur.close()
    conn.close()

    return result


def check_table_exists(host, port, user, password, db_name, table_name):
    "check if a table exists in a database"
    # establish connection
    try:
        conn = psycopg2.connect(
            f"host={host} port={port} dbname={db_name} user={user} password={password}"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        with cur as c:
            c.execute(
                f"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='{table_name}')"
            )
            table_exists = c.fetchone()[0]

        cur.close()
        conn.close()
    except:
        table_exists = False

    return table_exists


def process_corpus(
    user_name, corpus_name, own_urls, uploaded_document, passed_google_news
):
    "process an uploaded corpus"
    temp_directory = f"corpora/tmp_helper_{user_name}/"

    # make temporary directory to handle files
    if not os.path.exists(f"{temp_directory}"):
        os.makedirs(f"{temp_directory}")

    # if corpus name temporary, delete everything in the temporary files
    if corpus_name == f"temporary_{user_name}":
        if os.path.exists(f"corpora/{corpus_name}/"):
            shutil.rmtree(f"corpora/{corpus_name}/")
        if os.path.exists(f"corpora/metadata_{corpus_name}.csv"):
            os.remove(f"corpora/metadata_{corpus_name}.csv")
    try:
        # just sent a list of websites
        if own_urls != "":
            url_list = own_urls.split(",")
            metadata = pd.DataFrame(
                {"text_id": list(range(1, len(url_list) + 1)), "web_filepath": url_list}
            )

            # create the processor
            processor = nlp_processor(
                data_path=temp_directory,
                metadata_addt_column_names=[],
                windows_tesseract_path=windows_tesseract_path,
                windows_poppler_path=windows_poppler_path,
            )

            # sync the object's metadata to the local file
            for col in metadata.columns:
                processor.metadata[col] = metadata[col]

            # download the files
            processor.download_text_id(list(processor.metadata.text_id.values))

            # convert the files to text
            processor.convert_to_text(list(processor.metadata.text_id.values))

            # sync to the local metadata file
            processor.sync_local_metadata()

        else:
            if not (passed_google_news):
                # download the document
                with open(
                    f"{temp_directory}tmp.{uploaded_document.name.split('.')[-1]}", "wb"
                ) as new_file:
                    new_file.write(uploaded_document.getbuffer())
                    new_file.close()
            # google/google news/google scholar
            else:
                if (
                    server_state[f'{st.session_state["user_name"]}_gn_search']
                    == "Google News"
                ):
                    news_info = gen_google_news(
                        language=available_languages[
                            server_state[
                                f'{st.session_state["user_name"]}_gn_language'
                            ].lower()
                        ],
                        max_results=server_state[
                            f'{st.session_state["user_name"]}_gn_max_results'
                        ],
                        country=available_countries[
                            server_state[f'{st.session_state["user_name"]}_gn_country']
                        ],
                        start_date=server_state[
                            f'{st.session_state["user_name"]}_gn_date_range'
                        ][0],
                        end_date=server_state[
                            f'{st.session_state["user_name"]}_gn_date_range'
                        ][1],
                        search_term=server_state[
                            f'{st.session_state["user_name"]}_gn_query'
                        ],
                        site_list=[]
                        if server_state[f'{st.session_state["user_name"]}_gn_site_list']
                        == ""
                        else server_state[
                            f'{st.session_state["user_name"]}_gn_site_list'
                        ].split(","),
                    )
                elif (
                    server_state[f'{st.session_state["user_name"]}_gn_search']
                    == "Google search"
                ):
                    news_info = gen_google_search(
                        query=server_state[f'{st.session_state["user_name"]}_gn_query'],
                        language=available_languages[
                            server_state[
                                f'{st.session_state["user_name"]}_gn_language'
                            ].lower()
                        ],
                        max_results=server_state[
                            f'{st.session_state["user_name"]}_gn_max_results'
                        ],
                        country=available_countries[
                            server_state[f'{st.session_state["user_name"]}_gn_country']
                        ],
                        site_list=[]
                        if server_state[f'{st.session_state["user_name"]}_gn_site_list']
                        == ""
                        else server_state[
                            f'{st.session_state["user_name"]}_gn_site_list'
                        ].split(","),
                    )
                    
                    # for arxiv, return the PDF not the abstract
                    if server_state[f'{st.session_state["user_name"]}_gn_site_list'] == "arxiv.org":
                        for i in range(len(news_info)):
                            news_info[i]["url"] = news_info[i]["url"].replace("/abs/", "/pdf/")

                # create a synthetic metadata file
                uploaded_document = types.SimpleNamespace()
                uploaded_document.name = "metadata.csv"
                metadata_addt_column_names = [
                    "title",
                    "description",
                    "published_date",
                    "publisher",
                ]
                metadata = pd.DataFrame(
                    {
                        "text_id": list(range(1, len(news_info) + 1)),
                        "web_filepath": [x["url"] for x in news_info],
                        "title": [x["title"] for x in news_info],
                        "description": [x["description"] for x in news_info],
                        "published_date": [x["published date"] for x in news_info],
                        "publisher": [x["publisher"]["title"] for x in news_info],
                    }
                )

            # only uploaded a metadata CSV
            if uploaded_document.name == "metadata.csv":
                if not (passed_google_news):
                    metadata = pd.read_csv(f"{temp_directory}tmp.csv")
                    if "text_id" not in list(metadata.columns):
                        metadata["text_id"] = list(range(1, len(metadata) + 1))
                    metadata_addt_column_names = list(
                        metadata.columns[
                            ~metadata.columns.isin(
                                [
                                    "text_id",
                                    "web_filepath",
                                    "local_raw_filepath",
                                    "local_txt_filepath",
                                    "detected_language",
                                ]
                            )
                        ]
                    )

                # write metadata out
                processor = nlp_processor(
                    data_path=temp_directory,
                    metadata_addt_column_names=metadata_addt_column_names,
                    windows_tesseract_path=windows_tesseract_path,
                    windows_poppler_path=windows_poppler_path,
                )

                # sync the object's metadata to the local file
                for col in metadata.columns:
                    processor.metadata[col] = metadata[col]

                # download the files
                processor.download_text_id(list(processor.metadata.text_id.values))

                # select out PDF pages if available
                if "page_numbers" in processor.metadata.columns:
                    try:
                        processor.filter_pdf_pages(page_num_column="page_numbers")
                    except:
                        pass

                # convert the files to text
                processor.convert_to_text(list(processor.metadata.text_id.values))

                # sync to the local metadata file
                processor.sync_local_metadata()

            # uploaded a single .docx, .pdf, or .txt
            elif uploaded_document.name.split(".")[-1] in [
                "csv",
                "pdf",
                "docx",
                "doc",
                "txt",
            ]:
                # write metadata out
                processor = nlp_processor(
                    data_path=temp_directory,
                    metadata_addt_column_names=[],
                    windows_tesseract_path=windows_tesseract_path,
                    windows_poppler_path=windows_poppler_path,
                )

                # create metadata
                metadata = pd.DataFrame(
                    {
                        "text_id": 1,
                        "local_raw_filepath": f"{temp_directory}tmp.{uploaded_document.name.split('.')[-1]}",
                    },
                    index=[0],
                )

                # sync the object's metadata to the local file
                for col in metadata.columns:
                    processor.metadata[col] = metadata[col]

                # convert the files to text
                processor.convert_to_text(list(processor.metadata.text_id.values))

                # handle a CSV
                if (
                    "csv"
                    in f"{temp_directory}tmp.{uploaded_document.name.split('.')[-1]}"
                ):
                    old_name = f"{temp_directory}txt_files/1.txt"
                    os.remove(old_name)
                    new_name = f"{temp_directory}txt_files/1.csv"
                    shutil.copyfile(
                        f"{temp_directory}tmp.{uploaded_document.name.split('.')[-1]}",
                        new_name,
                    )
                    # update the metadata
                    processor.metadata.loc[0, "local_txt_filepath"] = new_name

            # uploaded a zip
            else:
                with ZipFile(f"{temp_directory}tmp.zip", "r") as zObject:
                    zObject.extractall(path=temp_directory)

                # sync the object's metadata to the local file
                provided_metadata = os.path.exists(f"{temp_directory}metadata.csv")

                if provided_metadata:
                    metadata = pd.read_csv(f"{temp_directory}metadata.csv")
                    metadata_addt_column_names = list(
                        metadata.columns[
                            ~metadata.columns.isin(
                                [
                                    "text_id",
                                    "web_filepath",
                                    "local_raw_filepath",
                                    "local_txt_filepath",
                                    "detected_language",
                                ]
                            )
                        ]
                    )
                    if "text_id" not in list(metadata.columns):
                        metadata["text_id"] = list(range(1, len(metadata) + 1))
                else:
                    file_list = [
                        x
                        for x in os.listdir(f"{temp_directory}corpus/")
                        if x.split(".")[-1] in ["csv", "txt", "docx", "doc", "pdf"]
                    ]

                    metadata = pd.DataFrame(
                        {
                            "text_id": list(range(1, len(file_list) + 1)),
                            "filename": file_list,
                        }
                    )
                    metadata_addt_column_names = []

                processor = nlp_processor(
                    data_path=temp_directory,
                    metadata_addt_column_names=metadata_addt_column_names,
                    windows_tesseract_path=windows_tesseract_path,
                    windows_poppler_path=windows_poppler_path,
                )

                for col in metadata.columns:
                    processor.metadata[col] = metadata[col]

                # put the files in the right place and update the metadata
                shutil.rmtree(f"{temp_directory}raw_files/")
                shutil.copytree(
                    f"{temp_directory}corpus/", f"{temp_directory}raw_files/"
                )

                for file in os.listdir(f"{temp_directory}raw_files/"):
                    processor.metadata.loc[
                        lambda x: x.filename == file, "local_raw_filepath"
                    ] = os.path.abspath(f"{temp_directory}raw_files/{file}")

                # select out PDF pages if available
                if "page_numbers" in processor.metadata.columns:
                    try:
                        processor.filter_pdf_pages(page_num_column="page_numbers")
                    except:
                        pass

                # convert the files to text
                processor.convert_to_text(list(processor.metadata.text_id.values))

                # handle a CSV
                for file in os.listdir(f"{temp_directory}raw_files/"):
                    if "csv" in file:
                        text_id = processor.metadata.loc[
                            lambda x: x.filename == file, "text_id"
                        ].values[0]
                        old_name = f"{temp_directory}txt_files/{text_id}.txt"
                        os.remove(old_name)
                        new_name = f"{temp_directory}txt_files/{text_id}.csv"
                        shutil.copyfile(f"{temp_directory}raw_files/{file}", new_name)
                        # update the metadata
                        processor.metadata.loc[
                            lambda x: x.filename == file, "local_txt_filepath"
                        ] = new_name

        ### upload type independent actions

        # move the .txt files to the appropriate place for RAG
        if os.path.exists(f"corpora/{corpus_name}/"):
            shutil.rmtree(f"corpora/{corpus_name}/")
        shutil.copytree(f"{temp_directory}txt_files/", f"corpora/{corpus_name}/")

        # adding file-path for application
        processor.metadata["file_path"] = [
            os.path.abspath(f"corpora/{corpus_name}/{x.split('/')[-1]}")
            for x in processor.metadata["local_txt_filepath"]
        ]
        processor.metadata.drop(
            ["is_csv", "local_raw_filepath", "local_txt_filepath", "detected_language"],
            axis=1,
            errors="ignore",
        ).to_csv(f"{temp_directory}metadata.csv", index=False)

        # move the metadata to the appropriate place for RAG
        processor.metadata.drop(
            ["is_csv", "local_raw_filepath", "local_txt_filepath", "detected_language"],
            axis=1,
            errors="ignore",
        ).to_csv(f"corpora/metadata_{corpus_name}.csv", index=False)

        # update the corpora list
        tmp_corpus = pd.DataFrame(
            {
                "name": corpus_name,
                "text_path": f"corpora/{corpus_name}/",
                "metadata_path": f"corpora/metadata_{corpus_name}.csv",
            },
            index=[0],
        )

        local_corpora_dict = pd.read_csv("metadata/corpora_list.csv")
        new_corpora_dict = pd.concat(
            [local_corpora_dict, tmp_corpus], ignore_index=True
        ).drop_duplicates()
        new_corpora_dict.to_csv("metadata/corpora_list.csv", index=False)

        # clear out the tmp_helper directory
        shutil.rmtree(temp_directory)
    except Exception as error:
        shutil.rmtree(temp_directory)
        raise ValueError(
            f"The following error arose while trying to process the corpus: {repr(error)}"
        )

    return new_corpora_dict
