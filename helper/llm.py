import streamlit as st


def gen_llm_call(messages=None):
    """Create the data required for an LLM call"""
    # llm url
    llm_url = (
        st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "llm_url"]
        .values[0]
    )

    # llm model name
    llm_model_name = (
        st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
        .values[0]
    )

    # llm api key
    st.session_state["llm_api_key"]

    st.session_state["temperature"]

    st.session_state["max_tokens"]

    system_prompt

    llm_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_api_key}",
    }


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
