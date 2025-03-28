def stream_response(query):
    """Stream LLM responses and allow stopping mid-stream."""
    # initial messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    llm_data = {
        "model": llm_model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True,
    }

    response = requests.post(
        API_URL, data=json.dumps(llm_data), headers=HEADERS, stream=True
    )
    output = ""

    # make sure this is st.write_stream somewhere
    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
        if st.session_state.stop_generation:
            break
        try:
            tokens = [
                json.loads(_)["delta"]["content"]
                for _ in re.findall(r"\[([^\]]*)\]", chunk)
            ]
            for token in tokens:
                yield token
                output += token
        except:
            pass

    return output
