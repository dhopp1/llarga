# streamlit_rag
A streamlit app for interfacing with a local LLM.

## Set up
- Install required libraries
- Download the LLM (in .gguf format) you would like to use and put it in the `models/` directory.
- Update the `metadata/llm_list.csv` file with the URL and local path of the model (`mistral-docsgpt` is recommended for RAG)
- If you would like to prepopulate a corpus outside of the app, add its name to the `metadata/corpora_list.csv` file in the `name` the file, the directory to the .txt files in the `text_path` column, and the path to the metadata file in the `metadata_path` column. The metadata file can contain anything, but must at least include a `text_id` column (unique identifier starting from 1) and a `file_path` column, containing the absolute path of all the text files in the corpus.
- In the `metadata/user_list.csv` file, put user names and emails. If the app is in use, it will tell you by who.
- run the app from the command line with `streamlit run app.py --server.port 8***` at whatever port you wish.
- To get the app online quickly, you can use [ngrok](https://www.sitepoint.com/use-ngrok-test-local-site/) to expose this local port to be able to access via the internet.

## User management
- The app has a password, which you can set by creating a `.streamlit/` directory in the base directory of the app, with a `secrets.toml` file inside containing `password = "desired_password"`
- You can change various theme options by creating a `.streamlit/config.toml` file, containin e.g.:

```
[theme]
primaryColor="#5b92E5"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
```

- Currently, the app supports only one concurrent user. The default behavior is to lock out other users while the app is in use. Other users will be locked out for 3 minutes from the last query run. You can change this length of time by changing this line: `st.session_state["available"] = (datetime.now() - st.session_state["last_used"]).total_seconds() > 180` in the `app.py` file.
- If a user has not run a query in 3 minutes, another user will be able to log on and the original user will be booted off.

## Changing model parameters
- Parameters are explained in the sidebar in their respective tooltips.
- Change their values then hit the `Reinitialize model` button to reinitialize the model with those parameters.
- The two parameters under `Vector DB parameters` require the recreation of the vector database, which may take longer if you have a very large corpus. If you change either of these, click the `Reinitialize model and remake DB` button instead.
- Hit the `Reset model's memory` button to clear the model's short-term memory/context.

## Uploading your own documents
- The system intializes with no corpus, so you are chatting with the vanilla LLM
- To query over your own documents, you have 6 options:
	1. Preprocess your files into .txts and place in the appropriate places according to the instructions in the "Set up" section. The corpus will then appear as an option under the `Which corpus` selector.
	2. Paste a comma-separated list of URLs into the `URLs` box. Make sure these URLs aren't behind a log in/paywall. If that is the case, copy the content to a Word or .txt file and upload directly.
	3. Upload/drag a single .doc, .docx, .pdf, or .txt file into the `Upload your own documents` box
	4. Upload a single `metadata.csv` file into the `Upload your own documents` box. The CSV can include any metadata you want, but must at least include a `web_filepath` column pointing to the website or PDF file online.
	5. Upload a .zip file containing many documents. Put all your documents into a directory called `corpus/`, then zip it. Upload that file into the `Upload your own documents` box.
	6. Upload a .zip file containing many documents as well as a metadata file. Put all your documents into a directory called `corpus/`, then put a file called `metadata.csv` at the same level as the `corpus/` directory (not _in_ directory), then zip the directory and CSV together. The CSV needs to have at least a column named `filename` with the filename of the documents. Upload that file into the `Upload your own documents` box.

- *Note*: Don't upload data .csv files, only a `metadata.csv` file. In the future I will build in an automatic way of parsing and handling these based off the `Chunk size` parameter. For now, you can preprocess your CSVs into .txt files by using the `local_rag_llm.db_setup.convert_csv` function from the [local\_rag\_llm](https://github.com/dhopp1/local_rag_llm/) library.
