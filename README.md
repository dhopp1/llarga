# streamlit_rag
A streamlit app for interfacing with a local LLM.

## Set up
- Install required libraries. The LLM and RAG system relies on two key libraries you should set up and make sure are working independently:
	- [nlp_pipeline](https://github.com/dhopp1/nlp_pipeline) for the processing of documents
	- [local\_rag\_llm](https://github.com/dhopp1/local_rag_llm) for the LLM itself
- Download the LLM (in .gguf format) you would like to use and put it in the `models/` directory.
- Update the `metadata/llm_list.csv` file with the URL and local path of the model (`mistral-docsgpt` is recommended for RAG)
- If you would like to prepopulate a corpus outside of the app, add its name to the `metadata/corpora_list.csv` file in the `name` the file, the directory to the .txt files in the `text_path` column, and the path to the metadata file in the `metadata_path` column. The metadata file can contain anything, but must at least include a `text_id` column (unique identifier starting from 1) and a `file_path` column, containing the absolute path of all the text files in the corpus.
- In the `metadata/user_list.csv` file, put user names and optionally emails.
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

- The app can support unlimited users. Simultaneous generation requests will be queued and executed in the order they are received. 
- All users share the same LLMs, so if you want to allow users to choose between multiple LLMs, you need to have enough VRAM to load them simultaneously. 
- Or, you can tick the `Clear other LLMs on reinitialize` checkbox under `Advanced model parameters`, which will clear all other LLMs (for all users) before loading the chosen model.

## Changing model parameters
- Parameters are explained in the sidebar in their respective tooltips.
- Most parameters can be changed and reflected at generation time. Exceptions are `Which LLM` and `Which corpus`, which when they are changed, need the `Reinitialize model` hit afterwards.
- The two parameters under `Vector DB parameters` require the recreation of the vector database, which may take longer if you have a very large corpus. If you change either of these, click the `Reinitialize model and remake DB` button instead.
- Hit the `Reset model's memory` button to clear the model's short-term memory/context. This is also necessary if you change the `System prompt` parameter.

## Uploading your own documents
- The system intializes with no corpus, so you are chatting with the vanilla LLM
- To query over your own documents, you have 7 options:
	1. Preprocess your files into .txts and place in the appropriate places according to the instructions in the "Set up" section. The corpus will then appear as an option under the `Which corpus` selector.
	2. Paste a comma-separated list of URLs into the `URLs` box. Make sure these URLs aren't behind a log in/paywall. If that is the case, copy the content to a Word or .txt file and upload directly.
	3. Upload/drag a single .csv, .doc, .docx, .pdf, or .txt file into the `Upload your own documents` box
	4. Upload a single `metadata.csv` file into the `Upload your own documents` box. The CSV can include any metadata you want, but must at least include a `web_filepath` column pointing to the website or PDF file online.
	5. Upload a .zip file containing many documents. Put all your documents into a directory called `corpus/`, then zip it. Upload that file into the `Upload your own documents` box.
	6. Upload a .zip file containing many documents as well as a metadata file. Put all your documents into a directory called `corpus/`, then put a file called `metadata.csv` at the same level as the `corpus/` directory (not _in_ directory), then zip the directory and CSV together. The CSV needs to have at least a column named `filename` with the filename of the documents. Upload that file into the `Upload your own documents` box.
	7. Fill in the `Google News query` parameter to create a corpus based on results from Google News.

- You can persist your corpus if it is large by typing a name other than `temporary` to the `Uploaded corpus name` box. This name will then appear as an option under the `Which corpus` dropdown. It should be lower case with no spaces or special characters, use underscores for spaces.
- Then hit the `Process corpus` button. This will both process the corpus and then reinitialize the model on this corpus, wait for both to finish.
- You can clear out old corpora from local files and the database by using `helper/clear_corpus.py`. E.g., run the command line in the `helper/` directory, then enter: 
	- `python clear_corpus.py --keep corpus1,corpus1` to delete everything except corpus1 and corpus2
	- `python clear_corpus.py --remove corpus1,corpus2` to remove only corpus1 and corpus2

## Managing the vector database
- Database credentials are stored in `metadata/db_creds.csv`
- For backing up, if you have `dump_on_exit` set to `1` in the `metadata/db_creds.csv` file, a database dump will be created each time a user exits the application in `corpora/vector_db_dump.sql`
- If you want to recreate the vector database in another place, for instance for running the application on a different computer, copy the entire `corpora/` directory to the new application and set `restore_db` to `1` in the `metadata/db_creds.csv` file. When you restart the server, when the first user logs into a new session, you will have to type the db password from `metadata/db_creds.csv` into the terminal to restore the database. This won't be required for subsequent log ons.
- Also make sure

## Example image
![Example image](metadata/example_screen.png)
