# streamlit_rag
A streamlit app for interfacing with a local LLM.

## Set up
- Install required libraries. The LLM and RAG system relies on two key libraries you should set up and make sure are working independently:
	- [nlp_pipeline](https://github.com/dhopp1/nlp_pipeline) for the processing of documents
	- [local\_rag\_llm](https://github.com/dhopp1/local_rag_llm) for the LLM itself
- Download the LLM (in .gguf format) you would like to use and put it in the `models/` directory (e.g., the Q5 quantization of Llama chat is available [here](https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf?download=true)).
- Update the `llm_path` field of the `metadata/llm_list.csv` file to reflect the location of the GGUF, and the `llm_url` field for your own reference.
- If you would like to prepopulate a corpus outside of the app, add its name to the `metadata/corpora_list.csv` file in the `name` the file, the directory to the .txt files in the `text_path` column, and the path to the metadata file in the `metadata_path` column. The metadata file can contain anything, but must at least include a `text_id` column (unique identifier starting from 1) and a `file_path` column, containing the absolute path of all the text files in the corpus.
- In the `metadata/user_list.csv` file, put user names and optionally emails.
- You can change the title of the application by changing the `app_title` column in the `metadata/settings.csv` file
- You can change the contact person by changing the `author_name` and `author_email` columns in the `metadata/settings.csv` file
- In `metadata/settings.csv`, in the `corpora_location` column, put the directory of your streamlit app and its `corpora/` directory. This is for management of the corpus metadata files, which use absolute paths because of the `nlp_pipeline` library
- You can change the context prompt by editing the `context_prompt` column in the `metadata/settings.csv` file. The `non_rag_system_prompt` is the default system prompt if you are not using RAG, `rag_system_prompt` is the default if you are. The system prompt can be changed from the front end as well.
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
- Database credentials are stored in `metadata/settings.csv`
- For backing up, if you have `dump_on_exit` set to `1` in the `metadata/settings.csv` file, a database dump will be created each time a user exits the application in `corpora/vector_db_dump.sql`
- If you want to recreate the vector database in another place, for instance for running the application on a different computer, copy the entire `corpora/` directory to the new application and set `restore_db` to `1` in the `metadata/settings.csv` file.

## Example image
![Example image](metadata/example_screen.png)

## Docker usage
### CPU only and CUDA
If only using the CPU or an Nvidia GPU, you can run the application exclusively with Docker.

- Download the `docker-compose.yml` and `Dockerfile` (for CPU-only) or `Dockerfile-gpu` (for GPU) files
- In `docker-compose.yml`, edit the HF_TOKEN to your API token
- There are four elements which need to exist outside of the container for persistence, portability, and personalization:
	- **`corpora/` directory**: this is where processed corpora (text files and vector database dumps) are saved. Change the `<local corpora directory>` line in `docker-compose.yml` to your local path for these files.
	- **`metadata/` directory**: this is where various information like database credentials, user list, llm list, etc. are stored. Change the `<local metadata directory>` line in `docker-compose.yml` to your local path for these files. The elements to be manually checked and changed are `settings.csv`, the `app_title`, `author_name`, and `author_email` columns, `llm_list.csv`, and `user_list.csv`.
	- **`models/` directory**: this is where the actual LLMs are stored. Change the `<local models directory>` line in `docker-compose.yml` to your local path for these files.
	- **`secrets.toml` file**: this is where you can change the application's password. Change the `<local secrets.toml file path>` line in `docker-compose.yml` to your local path for this file.
- If you are using the CPU, delete or comment out the `deploy:` section in `docker-compose.yml`, and change the `dockerfile: Dockerfile-gpu` line to `dockerfile: Dockerfile`.
- Navigate to the directory where you saved the `docker-compose.yml` file and Dockerfile and run `docker compose up`
- The application will now be available on port 8502 by default.

### Apple silicon
If you are using Apple silicon, you won't be able to run everything in Docker because of the lack of MPS drivers. You can still use the pgvector image however.

- follow the instructions to install [local\_rag\_llm](https://github.com/dhopp1/local_rag_llm/) and [nlp\_pipeline](https://github.com/dhopp1/nlp_pipeline) individually
- Download the `docker-compose.yml` file
- From the `docker-compose.yml` file, delete the `streamlit:` line and everything below it
- Start the postgres container with `docker compose up`
- Edit your `metadata/settings.csv` file and change the `host` column from `localhost` to `postgres` and `username` to `postgres`
- Run the application as normal.
