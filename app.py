import streamlit as stimport hmacimport pandas as pdimport sysimport gcfrom datetime import datetime, timedeltaimport timeimport osfrom streamlit_server_state import server_state, server_state_lockfrom helper.modelling import initializefrom helper.own_corpus import check_table_exists, check_db_exists, process_corpus, transfer_dbfrom helper.progress_bar import Logger### session initialization/login# how long between inactivity to lock a users session for in secondslast_used_threshold = 180max_users = 2user_log_path = "metadata/user_logs/"# user listif "users_list" not in st.session_state:    st.session_state["users_list"] = pd.read_csv("metadata/user_list.csv")# last used timesif not(os.path.exists(user_log_path)):    os.makedirs(user_log_path)# if never been used, availableif len([x for x in os.listdir(user_log_path) if ".txt" in x]) == 0:    st.session_state["available"] = Trueelse:    # if you can boot, set that booting person's to false    with server_state_lock["last_used"]:  # Lock the "count" state for thread-safety        server_state["last_used"] = {}        for user in st.session_state["users_list"].user:            try:                file = open(f'{user_log_path}{user.lower().replace(" ", "_")}.txt', "r")                server_state["last_used"][user] = datetime.strptime(file.read(), '%Y-%m-%d %H:%M:%S.%f')                file.close()            except:                server_state["last_used"][user] = datetime.now() - timedelta(hours=1, minutes=0)        server_state["locked"] = {}            for key, value in server_state["last_used"].items():            server_state["locked"][key] = (datetime.now() - value).total_seconds() < last_used_threshold        # is there a free spot    st.session_state["available"] = sum(server_state["locked"].values()) < max_users        # check if you are already in the list    if "user_name" in st.session_state:        if st.session_state["user_name"] is not None:            if server_state["locked"][st.session_state["user_name"]]:                st.session_state["available"] = True    # record a usagedef record_use(future_lock=False):    "record a usage, future lock to put it in the future for long running processes"    f = open(f'{user_log_path}{st.session_state["user_name"].lower().replace(" ", "_")}.txt', "w")    if future_lock:        f.write(str(datetime.now() + timedelta(hours=2, minutes=0)))    else:        f.write(str(datetime.now()))    f.close()# passworddef check_password():    """Returns `True` if the user had the correct password."""    if not(st.session_state["available"]):        # people currently using it        current_users = sorted([k for k, v in server_state["locked"].items() if v])        current_emails = [st.session_state["users_list"].loc[lambda x: x.user == user, "email"].values[0] for user in current_users]                error_string = "Application in use by:\n\n"                for i in range(len(current_users)):            error_string += f"[{current_users[i]}](mailto:{current_emails[i]})\n\n"                error_string += "Refresh in 3 minutes, if someone has stopped using it you will be able to log in."        st.error(error_string)    def password_entered():        """Checks whether a password entered by the user is correct."""        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):            st.session_state["password_correct"] = True            del st.session_state["password"]  # Don't store the password.        else:            st.session_state["password_correct"] = False    # Return True if the password is validated.    if st.session_state.get("password_correct", False):        if st.session_state["available"]:            return True        # show input for user name    st.session_state["user_name"] = st.selectbox(       "User",       st.session_state["users_list"],       index=None,       placeholder="Select user...",    )    # Show input for password.    st.text_input(        "Password", type="password", on_change=password_entered, key="password"    )    if "password_correct" in st.session_state:        st.error("Password incorrect")    return Falseif not check_password():    st.stop()  # Do not continue if check_password is not True.    ###  app setup# headerst.title("Local LLM")master_db_name = "vector_db"if "db_name" not in st.session_state:    st.session_state["db_name"] = st.session_state["user_name"].lower().replace(" ", "_")    # clear out this users old models if they existdef clear_models():    if f'model_{st.session_state["db_name"]}' in server_state:        try:            server_state[f'model_{st.session_state["db_name"]}'].close_connection()        except:            pass        del server_state[f'model_{st.session_state["db_name"]}'].llm        del server_state[f'model_{st.session_state["db_name"]}']        gc.collect()# checking if first boot of userif "first_boot" not in st.session_state:    st.session_state["first_boot"] = True    if "queue" not in server_state:        server_state["queue"] = [st.session_state["user_name"]]    else:        server_state["queue"] += [st.session_state["user_name"]]else:    st.session_state["first_boot"] = False    if st.session_state["first_boot"]:    clear_models()# checking if first boot of serverif "first_boot" not in server_state:    server_state["first_boot"] = Trueelse:    server_state["first_boot"] = Falseif server_state["first_boot"]:    # set generating to false on first boot    f = open("metadata/generating.txt", "w")    f.write(str(False))    f.close()# Do not continue if a new user has booted off this oneprint(f'last user: {server_state["queue"][-1]}')if not(server_state["locked"][st.session_state["user_name"]]) and len(server_state["queue"]) >= max_users:    if server_state["queue"][0] == st.session_state["user_name"]:        server_state["queue"] = server_state["queue"][1:]        st.error("""Someone new has logged on. Refresh in 3 minutes, if someone has stopped using it you will be able to log in.""")        clear_models()        st.stop()        # styles sheetswith open( "styles/style.css" ) as css:    st.markdown( f'<style>{css.read()}</style>' , unsafe_allow_html= True)    user_avatar = "https://www.svgrepo.com/show/524211/user.svg"#"\N{grinning face}"assistant_avatar = "https://www.svgrepo.com/show/375527/ai-platform.svg"#"\N{Robot Face}"# LLM set up# parameters/authenticationllm_dict = pd.read_csv("metadata/llm_list.csv")corpora_dict = pd.read_csv("metadata/corpora_list.csv")db_info = pd.read_csv("metadata/db_creds.csv")# placeholder on initial loadif f'model_{st.session_state["db_name"]}' not in server_state:    st.markdown("""<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""", unsafe_allow_html=True)    st.markdown("""<div class="icon_text"<h4>How do I start?</h4></div>""", unsafe_allow_html=True)    st.markdown("""<div class="icon_text"<h4>1) Upload your own documents/put in your own URLs then hit the 'Process corpus' button</h4></div>""", unsafe_allow_html=True)    st.markdown("""<div class="icon_text"<h4>2) Select a prebuilt corpus from the 'Which corpus' dropdown then hit the 'Reinitialize model' button</h4></div>""", unsafe_allow_html=True)    st.markdown("""<div class="icon_text"<h4>3) Hit the 'Reinitialize model' button if you want to talk to the vanilla LLM</h4></div>""", unsafe_allow_html=True) ## sidebar# upload your own documents    st.sidebar.markdown("# Upload your own documents", help = "Enter the name of your corpus in the `Corpus name` field. If named `temporary`, it will be able to be written over after your session.")# paste a list of web urlsst.session_state["own_urls"] = st.sidebar.text_input(   "URLs",   value="" if "own_urls" not in st.session_state else st.session_state["own_urls"],   help="A comma separated list of URLs.")st.session_state["uploaded_file"] = st.sidebar.file_uploader("Upload your own documents",type=[".zip", ".docx", ".doc", ".txt", ".pdf", ".csv"], help="Upload either a single `metadata.csv` file, with at least one column named `web_filepath` with the web addresses of the .html or .pdf documents, or upload a .zip file that contains a folder named `corpus` with the .csv, .doc, .docx, .txt, or .pdf files inside. You can optionally include a `metadata.csv` file in the zip file at the same level as the `corpus` folder, with at least a column named `filename` with the names of the files. If you want to only include certain page numbers of PDF files, in the metadata include a column called 'page_numbers', with the pages formatted as e.g., '1,6,9:12'.")st.session_state["new_corpus_name"] = st.sidebar.text_input(   "Uploaded corpus name",   value=f"temporary_{st.session_state['db_name']}" if "new_corpus_name" not in st.session_state else st.session_state["new_corpus_name"],   help="The name of the new corpus. It must be able to be a SQL database name, so only lower case, no special characters, no spaces. Use underscores.")with st.sidebar.form("corpus_buttons"):    process_corpus_button = st.form_submit_button('Process corpus')    reset_memory = st.form_submit_button("Reset model's memory")# model paramsst.sidebar.markdown("# Model parameters", help="Click the `Reinitialize model` button if you change any of these parameters.")# which_llmst.session_state["selected_llm"] = st.sidebar.selectbox(   "Which LLM",   options=llm_dict.name,   index=tuple(llm_dict.name).index("mistral-docsgpt") if "selected_llm" not in st.session_state else tuple(llm_dict.name).index(st.session_state["selected_llm"]),   help="Which LLM to use.")# which corpusst.session_state["selected_corpus"] = st.sidebar.selectbox(   "Which corpus",   options=["None"] + sorted([x for x in list(corpora_dict.name) if "temporary" not in x or x == f"temporary_{st.session_state['db_name']}"]), # don't show others' temporary corpora   index=0 if "selected_corpus" not in st.session_state else tuple(["None"] + sorted([x for x in list(corpora_dict.name) if "temporary" not in x or x == f"temporary_{st.session_state['db_name']}"])).index(st.session_state["selected_corpus"]),   help="Which corpus to contextualize on.")# similarity top kst.session_state["similarity_top_k"] = st.sidebar.slider(   "Similarity top K",   min_value=1,   max_value=20,   step=1,   value=4 if "similarity_top_k" not in st.session_state else st.session_state["similarity_top_k"],   help="The number of contextual document chunks to retrieve for RAG.")# n_gpu layersst.session_state["n_gpu_layers"] = 100 if "n_gpu_layers" not in st.session_state else st.session_state["n_gpu_layers"]# temperaturest.session_state["temperature"] = st.sidebar.slider(   "Temperature",   min_value=0,   max_value=100,   step=1,   value=0 if "temperature" not in st.session_state else st.session_state["temperature"],   help="How much leeway/creativity to give the model, 0 = least creativity, 100 = most creativity.")# max_new tokensst.session_state["max_new_tokens"] = st.sidebar.slider(   "Max new tokens",   min_value=16,   max_value=16000,   step=8,   value=512 if "max_new_tokens" not in st.session_state else st.session_state["max_new_tokens"],   help="How long to limit the responses to (token ≈ word).")# context windowst.session_state["context_window"] = st.sidebar.slider(   "Context window",   min_value=500,   max_value=50000,   step=100,   value=4000 if "context_window" not in st.session_state else st.session_state["context_window"],   help="How large to make the context window for the LLM. The maximum depends on the model, a higher value might result in context window too large errors.")# memory limitst.session_state["memory_limit"] = st.sidebar.slider(   "Memory limit",   min_value=80,   max_value=80000,   step=8,   value=2048 if "memory_limit" not in st.session_state else st.session_state["memory_limit"],   help="How many tokens (words) memory to give the chatbot.")# system promptst.session_state["system_prompt"] = st.sidebar.text_input(   "System prompt",   value=""  if "system_prompt" not in st.session_state else st.session_state["system_prompt"],   help="What prompt to initialize the chatbot with.")# params that affect the vector_dbst.sidebar.markdown("# Vector DB parameters", help="Changing these parameters will require remaking the vector database and require a bit longer to run. Push the `Reinitialize model and remake DB` button if you change one of these.")# chunk overlapst.session_state["chunk_overlap"] = st.sidebar.slider(   "Chunk overlap",   min_value=0,   max_value=1000,   step=1,   value=200 if "chunk_overlap" not in st.session_state else st.session_state["chunk_overlap"],   help="How many tokens to overlap when chunking the documents.")# chunk sizest.session_state["chunk_size"] = st.sidebar.slider(   "Chunk size",   min_value=64,   max_value=6400,   step=8,   value=512 if "chunk_size" not in st.session_state else st.session_state["chunk_size"],   help="How many tokens per chunk when chunking the documents.")# reinitialize model buttonwith st.sidebar.form("model_buttons"):    reinitialize = st.form_submit_button('Reinitialize model')    reinitialize_remake = st.form_submit_button('Reinitialize model and remake DB')    # help contactst.sidebar.markdown("*For questions on how to use this application or its methodology, please write [Author](mailto:someone@example.com)*", unsafe_allow_html=True)    # static model paramsparagraph_separator = "\n\n\n"separator = " "use_chat_engine = Truereset_chat_engine = Falseif "rerun_populate_db" not in st.session_state:    st.session_state["rerun_populate_db"] = Falseif "clear_database" not in st.session_state:    st.session_state["clear_database"] = False    # reinitialize the vector db for simultaneous access initiallyif "reinitialized_db" not in st.session_state:    st.session_state["reinitialized_db"] = Falseelse:    st.session_state["reinitialized_db"] = True    if not(st.session_state["reinitialized_db"]):    # only run if database exists    if check_db_exists(user=db_info.loc[0, 'user'], password=db_info.loc[0, 'password'], db_name=master_db_name):        transfer_db(user=db_info.loc[0, 'user'], password=db_info.loc[0, 'password'], source_db=master_db_name, target_db=st.session_state["db_name"])# loading model#if f'model_{st.session_state["db_name"]}' not in server_state or reinitialize or reinitialize_remake or process_corpus_button:if reinitialize or reinitialize_remake or process_corpus_button:    if process_corpus_button:        if not((st.session_state["new_corpus_name"] == f"temporary_{st.session_state['db_name']}") or (st.session_state["new_corpus_name"] not in list(corpora_dict.name.values))):            st.error("A corpus with this name already exists, choose another one.")        else:            with st.spinner('Processing corpus...'):                record_use(future_lock=True)                old_stdout = sys.stdout                sys.stdout = Logger(st.progress(0), st.empty())                corpora_dict = process_corpus(user_name=st.session_state["db_name"], corpus_name=st.session_state["new_corpus_name"], own_urls=st.session_state["own_urls"], uploaded_document=st.session_state["uploaded_file"])                record_use(future_lock=False)                            st.session_state["selected_corpus"] = st.session_state["new_corpus_name"]            st.session_state.messages = [] # clear out message history on the prior context            clear_models()        with st.spinner('Initializing...'):        # whether or not to remake the vector DB        if reinitialize_remake or process_corpus_button:            rerun_populate_db = True            clear_database_local = st.session_state["clear_database"]        else:            rerun_populate_db = st.session_state["rerun_populate_db"]            clear_database_local = st.session_state["clear_database"]                    def model_initialization():            model, st.session_state["which_llm"], st.session_state["which_corpus"] = initialize(                which_llm_local=st.session_state["selected_llm"],                which_corpus_local=None if st.session_state["selected_corpus"] == "None" else st.session_state["selected_corpus"],                n_gpu_layers=st.session_state["n_gpu_layers"],                temperature=st.session_state["temperature"] / 1e2, # convert 1-100 to 0-1                max_new_tokens=st.session_state["max_new_tokens"],                context_window=st.session_state["context_window"],                memory_limit=st.session_state["memory_limit"],                chunk_overlap=st.session_state["chunk_overlap"],                chunk_size=st.session_state["chunk_size"],                paragraph_separator=paragraph_separator,                separator=separator,                system_prompt=st.session_state["system_prompt"],                rerun_populate_db=rerun_populate_db,                clear_database_local=clear_database_local,                corpora_dict=corpora_dict,                llm_dict=llm_dict,                db_name=st.session_state["db_name"],                db_info=db_info,            )            server_state[f'model_{st.session_state["db_name"]}'] = model            del model            gc.collect()                print("WOW GOT HERE")        record_use(future_lock=True)        model_initialization()        record_use(future_lock=False)        print("WOW GOT HERE 2.0")                # clear the progress bar        if rerun_populate_db:            sys.stdout = sys.stdout.clear()            sys.stdout = old_stdout                    # copy the new table to master vector_db if it's not already there        if not(check_table_exists(user=db_info.loc[0, 'user'], password=db_info.loc[0, 'password'], db_name=master_db_name, table_name=f"data_{st.session_state['which_corpus']}")):            # close the model connection to not have simulataneous ones            clear_models()                        # transfer the db            transfer_db(user=db_info.loc[0, 'user'], password=db_info.loc[0, 'password'], source_db=st.session_state["db_name"], target_db=master_db_name)                        # reinitialize the model            record_use(future_lock=True)            model_initialization()            record_use(future_lock=False)                    st.session_state.messages = [] # clear out message history on the prior context        st.info("Model successfully initialized!")if f'model_{st.session_state["db_name"]}' in server_state:    # Initialize chat history    if "messages" not in st.session_state:        st.session_state.messages = []        # Display chat messages from history on app rerun    for message in st.session_state.messages:        avatar = user_avatar if message["role"] == "user" else assistant_avatar        with st.chat_message(message["role"], avatar=avatar):            if "source_string" not in message["content"]:                st.markdown(message["content"])            else:                st.markdown("Sources: ", unsafe_allow_html=True, help=message["content"].split("string:")[1])                    # reset model's memory    if reset_memory:        if server_state[f'model_{st.session_state["db_name"]}'].chat_engine is not None:            server_state[f'model_{st.session_state["db_name"]}'].chat_engine.reset()        with st.chat_message("assistant", avatar=assistant_avatar):            st.markdown("Model memory reset!")        st.session_state.messages.append({"role": "assistant", "content": "Model memory reset!"})        # Accept user input    if st.session_state["which_corpus"] is None:        placeholder_text = f"""Query '{st.session_state["which_llm"]}', not contextualized"""    else:        placeholder_text = f"""Query '{st.session_state["which_llm"]}' contextualized on '{st.session_state["which_corpus"]}' corpus"""            if prompt := st.chat_input(placeholder_text):        # Display user message in chat message container        with st.chat_message("user", avatar=user_avatar):            st.markdown(prompt)        # Add user message to chat history        st.session_state.messages.append({"role": "user", "content": prompt})                if st.session_state.messages[-1]["content"].lower() == "clear":            clear_models()                with st.chat_message("assistant", avatar=assistant_avatar):                st.markdown("Models cleared!")            st.session_state.messages.append({"role": "assistant", "content": "Models cleared!"})        else:            # lock the model to perform requests sequentially            if "in_use" not in st.session_state:                file = open("metadata/generating.txt", "r")                st.session_state["in_use"] = eval(file.read())                file.close()                            with st.spinner('Query queued...'):                while st.session_state["in_use"]:                    file = open("metadata/generating.txt", "r")                    st.session_state["in_use"] = eval(file.read())                    file.close()                    time.sleep(5)                                f = open("metadata/generating.txt", "w")            f.write(str(True))            f.close()                        record_use(future_lock=True)                            # generate response                            response = server_state[f'model_{st.session_state["db_name"]}'].gen_response(                st.session_state.messages[-1]["content"],                similarity_top_k=st.session_state["similarity_top_k"],                use_chat_engine=use_chat_engine,                reset_chat_engine=reset_chat_engine,                streaming=True,            )            def streamed_response(streamer):                with st.spinner('Thinking...'):                    for token in streamer.response_gen:                        yield token                                    # Display assistant response in chat message container            with st.chat_message("assistant", avatar=assistant_avatar):                st.write_stream(streamed_response(response["response"]))                    # adding sources            with st.chat_message("assistant", avatar=assistant_avatar):                if len(response.keys()) > 1: # only do if RAG                    # markdown help way                    source_string = ""                    counter = 1                    for j in list(pd.Series(list(response.keys()))[pd.Series(list(response.keys())) != "response"]):                        #source_string += f"**Source {counter}**:\n\n \t\t{response[j]}\n\n\n\n"                        metadata_dict = eval(response[j].split("| source text:")[0].replace("metadata: ", ""))                        metadata_string = ""                        for key, value in metadata_dict.items():                            if key != "is_csv":                                metadata_string += f"'{key}': '{value}'\n"                                                source_string += f"""# Source {counter}\n ### Metadata:\n ```{metadata_string}```\n ### Text:\n{response[j].split("| source text:")[1]}\n\n"""                        counter += 1                else:                    source_string = "NA"                st.markdown("Sources: ", unsafe_allow_html=True, help = f"{source_string}")                            # unlock the model            f = open("metadata/generating.txt", "w")            f.write(str(False))            f.close()                        record_use(future_lock=False)                    # Add assistant response to chat history            st.session_state.messages.append({"role": "assistant", "content": response["response"].response})            st.session_state.messages.append({"role": "assistant", "content": f"source_string:{source_string}"})