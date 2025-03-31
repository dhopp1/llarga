from datetime import datetime
import json
import re
import requests
import streamlit as st


def gen_llm_response(query, messages=[]):
    """Create the data required for an LLM call"""
    messages = messages.copy()

    # llm url
    llm_url = (
        st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "llm_url"]
        .values[0]
    ) + "/chat/completions"

    # llm model name
    llm_model_name = (
        st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
        .values[0]
    )

    # messages = empty = first call
    if len(messages) == 0:
        messages = [
            {"role": "system", "content": st.session_state["system_prompt"]},
            {"role": "user", "content": query},
        ]
    else:
        messages += [{"role": "user", "content": query}]

    llm_headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {st.session_state["llm_api_key"]}',
    }

    llm_data = {
        "model": llm_model_name,
        "temperature": st.session_state["temperature"],
        "max_tokens": st.session_state["max_tokens"],
        "messages": messages,
        "stream": True,
    }

    response = requests.post(
        llm_url, headers=llm_headers, data=json.dumps(llm_data), stream=True
    )
    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
        if st.session_state["stop_generation"]:
            st.session_state["generating"] = False
            break
        try:
            tokens = [
                json.loads(_)["delta"]["content"]
                for _ in re.findall(r"\[([^\]]*)\]", chunk)
            ]
            for token in tokens:
                yield token
        except:
            pass

    yield f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
