# Llarga
Llarga stands for 'Local Large language RAG Application'. A streamlit application for using RAG with any LLM, cloud or local, without the need for a vector database.

# User guide
This section contains information for users of the application. For reference, RAG stands for Retrieval-Augmented Generation and is a method of providing an LLM with new information outside of its training data.

## Chat interface
- **Main section**: the main section of the application contains your chat and a field at the bottom to enter your questions.
- **Streaming response**: when you ask your question, the LLM response will appear one word at a time as the answer is generated. You can hit the `Stop generating` button that appears next to your question at any time to stop the LLM from generating further, for instance if your question has already been answered and you don't want to wait for it to finish to ask your next question. However far the LLM generated will be saved to your chat history.
- **Source hover**: at the bottom of each LLM response, you will see the word `Sources:` with a question mark after it. You can hover over this question mark to see information about how the LLM answered your query (the hover is scrollable), including which LLM generated the response, which corpus/knowledge base was used to answer the question, and the LLM's style when it generated the response (e.g., more creative or more precise). If you used a corpus/knowledge base, you will also find in the hover the excerpts from the source documents the LLM was given to answer your question, along with each excerpt's metadata.

## Sidebar
### Chats
- **Select chat**: this dropdown contains your previous chats. You can select any and continue where you left off by asking a new question in the chat interface. You can even switch which LLM you are using in the middle of a chat. Create a new chat with the `New chat` button, and delete an old one with the `Delete chat` button. Chat histories are stored only on the server where the application is being run from.

### Corpus
- **Currently loaded corpus**: this dropdown shows a list of available corpora/knowledge bases. A corpus is a collection of documents (e.g., reports or schedules) you want the LLM to be aware of. `No corpus` means that RAG will not be used, and you are chatting with the "vanilla" or non-contextualized LLM. `Workspace` is your personal corpus you can overwrite repeatedly and use as a scratch corpus that you don't necessarily need to keep available in the long term.
- **Corpus metadata**: if you have selected a corpus other than `No corpus`, this expander will show you the metadata for that corpus. 
	- You can check or uncheck documents in the table's `Include in queries` column to only search some documents from your corpus. For instance, if your corpus contains annual reports for the last 10 years, but you know for this particular question you are only interested in last year's report, you can check only that report's `Include in queries` column and the LLM will only answer based on that document. The metadata table is scrollable and expandable by hovering over it and clicking the `Fullscreen` square icon that appears.
	-  Click the `Select all` button to select all documents
	-  Click the `Unselect all` button to deselect all documents
	-  Once you have checked/ticked which documents you would like to include in the search, click the `Save selection` button to persist the selection.
	-  You can have the LLM choose which documents to include in your query based on the metadata and natural-langauge instructions. Put your instructions in the text box above the `Select documents with LLM` button, then hit the button to have the LLM choose which documents to select. For instance, if you have a `Year` column in your metadata, you could provide an instruction like, `select only documents after 2017`. You can then verify and alter the LLM's selection by interacting with the metadata table directly. Performance of this features will depend on the quality of LLM you have selected. Private/local LLMs will perform worse in this feature.
	-  Click the `Download corpus converted to text` button to generate a .zip file with the .txt converted files of your corpus. After you click, the file will be generated, then click the `Download` button to download.

### Upload your own documents
- **Upload a new corpus**: use this file uploader to upload your own custom corpus to the system. You can provide the new corpus in 4 ways:
	- upload a single file. Supported formats are:
		- _.docx_
		- _.doc_
		- _.txt_
		- _.pdf_
		- _.csv_: for csv, xlsx, and xls, the data will be converted to markdown tables so the LLM can parse it more easily. Only the first sheet will be converted for Excel files
		- _.xlsx_
		- _.xls_
		- _.pptx_: note, the older `.ppt` format is not supported. Convert these to `.pptx` in PowerPoint BEFORE zipping and uploading them to the system.
		- _.mp3_: audio and video files will be automatically converted to text
		- _.m4a_
		- _.wav_
		- _.mp4_
	- upload a single `metadata.csv` file with at least one column called `web_filepath` with the URLs of the documents you would like in the corpus. You can provide additional columns with more metadata. The URLs must lead directly to the content page you would like (e.g., the URL directly to the PDF file itself, not the landing page where it is linked). The file must be named **exactly** `metadata.csv` and the URL column must be named **exactly** `web_filepath` or the upload will not work.
	- upload a zip file with multiple documents zipped together
	- upload a zip file with the documents plus a `metadata.csv` file (named exactly that). To link the metadata information to the files, the metadata file must have at least one column called `filepath` containing the file name of each file in the zipped folder
- **Name for new corpus**: what you would like this corpus to be called. This is what will appear as an option in the `Currently loaded corpus` dropdown. If you choose a name where there is an existing corpus, you will be shown a warning, but you can overwrite it if you are sure it was you who created it.
- **Who should corpus be accessible by?**: when uploading a new corpus, you can choose who should be able to access the corpus. If you leave this field blank, every user of the applicaiton will be able to access the corpus. If you choose only your name, the corpus will only be visible to you. You can select multiple people to make the corpus available to.
- **Is this a confidential corpus?**: check this box when processing your documents to restrict them from being able to be queried from any cloud provider. Only LLMs with `(private)` in the name can query them.
- **Process corpus button**: once you have uploaded your file, click this button to process it and make it available to the LLM. This may take a while depending on the size and complexity of your corpus (e.g., lots of audio files or OCR PDFs, etc.)
- **Delete a corpus**: Enter the name of a corpus you want to delete, then hit the `Delete corpus` button to remove it.

### LLM parameters
- **Search the web with your query?**: check if you would like to search the web with your query for additional context information before sending it to the LLM. Alternatively, you can enter just a complete URL (i.e., with `https://...`) or comma-separated list of URLs as your prompt to fetch their content and make it available to the LLM. The LLM will have an initial prompt to summarize the page(s), but you can ask follow up questions on the full content of the URLs.
- **Cite sources?**: check if you would like to return in-text references to document metadata and page numbers. Performance depends on the power of the LLM.
- **Select LLM**: choose which LLM you would like to use. Those ending in `(private)` are local LLMs. That means that any query you send does not leave the server where the application is running, so is safe for use for sensitive or confidential documents. Those ending in `(cloud)` are generally much more powerful and performant models, but your query will be sent to their servers for processing.
- **Paste API key here**: if you choose a cloud model that requires an API key and your administrator hasn't provided a default one, you will be notified that you need to paste your own API key in this field in order to be able to use the LLM. The pasted API key is not stored or saved anywhere, even on the server where the application is running.
- **Model style**: this dropdown determines the level of creativity/freedom given to the model. `Most precise` is the least creative and will stick closest to your prompts and the documents. `Most creative` is the most creative/unpredictable, useful for ideation, etc.
- **Use default system prompts**: if checked, the LLM will be given the default system prompts (baseline instructions for the LLM) for the corpora you are working with. If unchecked, you are free to enter your own system prompt. System prompts will take effect when a new chat is started.
- **System prompt**: baseline instructions of the model it will consider during every question that is asked. You can change the default system prompt for a newsly processed corpus by unchecking `Use default system prompts`, entering your own system prompt, then hitting the `Process corpus` button.
- **Stop Llama CPP server**: as a user, this button can be ignored. It just stops the local LLM server to free up memory on the machine hosting the application.

### Batch query
You can upload an excel file to ask multiple questions in a loop to the LLM.

- **Download a template excel file**: click this button to download a template of how the system expects batch query requests. It requires two column, `query`, which contains the question you want to ask, and `text_ids`, containing a comma-separated list of text ids you want the LLM to consider when answering your question. You can find documents' text ids by looking in the metadata table under the `Corpus metadata` expander. You can ask the same question multiple times, just changing the documents you want the LLM to consider when answering.
- **Upload bulk query file**: upload your filled in batch query template Excel file here.
- **Run batch query**: click this button to run your batch query. It will ask the questions in the chat you currently have open, so it makes sense to start a new chat before hitting this button. You will then see each question answered live on the screen. In batch query mode, each question is asked as a standalone question, so there is no chat memory. When it is complete, you can download the results by clicking the `Export chat history as Excel file` button. If your run is interrupted (say you accidentally close the window), you can go back to that chat, reupload your file, and pick up where you left off without starting over from the beginning. If you want to start over from the beginning, just create a new chat and start the run again.

### Export chat
Click the `Export chat history as Excel file` to download the selected chat as an Excel file. This will give you information on which LLM and which settings were used, what the system prompt was, and was sources/documents the LLM used to answer your questions (in the `source_metadata` and `source_content` columns).

# Admin guide
## Installation
- git clone this repo
- install [nlp\_pipeline](https://github.com/dhopp1/nlp_pipeline) and [local\_vector\_search](https://github.com/dhopp1/local_vector_search/) and the dependencies in their `requirements.txt`. For `nlp_pipeline` you may need to install all but `xlrd`, then install `xlrd==2.0.1` manually afterwards.
- If you plan to use a local LLM with [llamacpp](https://github.com/ggml-org/llama.cpp), you need to install it (for instance with `brew install llama.cpp` on a Mac). 
- Alternatively, you can call `docker compose -f docker-compose.yml up` (or `docker-compose-gpu.yml` if you have an Nvidia GPU), being sure to change the directory locations for your settings/etc. files and setting the port numbers to your desired values.

## Settings
### metadata/llm_list.csv
In this file you can specify which LLMs you want to make available to the system. Explanation of the columns:

- **name**: display name (in the `Select LLM` dropdown) of the model
- **llm_url**: API endpoing of the LLM. Use `http://localhost:[desired port number]/v1` for local llama cpp models. If using docker and you want to access a llamacpp server on the host machine (necessary for instance for Macs), you should map the ports in your `docker-compose.yml` file and enter `http://host.docker.internal:[desired port number]/v1` in this column instead of `localhost`.
- **model_name**: the name of the model necessary for the  API call. For a local LLM, the path the the .gguf file of the LLM.
- **api_key**: the API key for this model. `no-key` for llamacpp models. If you don't want to provide a default key to the app and rather want the user to enter their own in the `Paste API key here` field, enter `API_KEY` in this field and the user will be notified they need to provide their own key.
- **context_length**: the context length of the LLM
- **reasoning_model**: `1` if the model is a reasoning model (like Deepseek R1), `0` otherwise.
- **display**: `1` if you want the LLM to be displayed as an option to the user, `0` otherwise.

### metadata/settings.csv
Various settings of the app. Explanation of fields:

- **app_title**: the title of the app to be dispayed on the tab and at the top fo the site.
- **default\_no\_corpus\_system_prompt**: the default system prompt for an LLM with no corpus loaded (non-RAG)
- **default\_corpus\_system\_prompt**: the default system prompt for an LLM with a corpus loaded (RAG-enabled)
- **max_tokens**: the max number of tokens the LLM can output.
- **chunk_size**: the number of tokens each chunk is when embedding and chunking the documents.
- **chunk_overlap**: the number of tokens of overlap each chunk has, to avoid splitting sentences in the middle and not having the complete thought contained in any chunk.
- **context\_window\_rag\_ratio**: number from 0 to 1. What percent of the context window of the LLM to use for the RAG context. This will dynamically determine the number of chunks based on the chunk size and the context window of the LLM. You would want to be less than 1 to have room for chat memory in the LLM's context window.
- **manage\_llama\_cpp**: `1` if you want the app to dynamically manage your llamacpp servers, hot switching between different models, managing queue, etc. `0` if you will manage the llamacpp server outside of the app.
- **use\_condensed\_lvs\_query**: `1` if you want the LLM to condense follow-up queries to standalone questions before querying the embeddings to ensure the retrieval of relevant documents. Takes a little bit more time. `0` if you just want to send the user question as is to the vector search.
- **llama\_server\_command**: If llama-server isn't in your path, the full path to llama-server. Should be `/app/llama-server` for the GPU docker file.
- **llama\_server\_cwd**: If llama-server isn't in your path, where the llama-server command needs to be run from. Should be `/app` for the GPU docker file.
- **llama\_server\_n\_gpu\_layers**: Number of layers to offload to the GPU.
- **llama\_server\_show\_stop\_button**: `1` if you want the stop Llama CPP server button to show, `0` if not.

### metadata/user_list.csv
A list of users for the application. Their display name in the `user` column, what their default corpus should be upon first loadup in the `default_corpus` column. Each user gets their own password, which can be set in the `.streamlit/secrets.toml` file. Each user on a new line with their own password. Replace spaces with underscores in the `secrets.toml` file. For instance, if the user's name is `Test User`, it should appear as `Test_User = "password"` in the `secrets.toml` file.

## Running the application
From the cloned repo, run the application with `streamlit run app.py --server.headless=true --server.port=[desired port]`. You can then use the app by going to `http://localhost:[desired port]`
