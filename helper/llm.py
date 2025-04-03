from datetime import datetime
from openai import OpenAI
import streamlit as st

from helper.user_management import lock_llm, unlock_llm


def gen_llm_response(query, messages_input=[]):
    """Create the data required for an LLM call"""
    messages = messages_input.copy()

    # modifying prompt to remove time
    messages[-1]["content"] = messages[-1]["content"].split("<br> <sub>")[0]

    # adding RAG if necessary

    # llm model name
    llm_model_name = (
        st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
        .values[0]
    )

    client = OpenAI(
        api_key=st.session_state["llm_api_key"],
        base_url=st.session_state["llm_info"]
        .loc[lambda x: x["name"] == st.session_state["selected_llm"], "llm_url"]
        .values[0],
    )

    response = client.chat.completions.create(
        model=llm_model_name,
        temperature=st.session_state["temperature"],
        max_tokens=st.session_state["max_tokens"],
        messages=messages,
        stream=True,
    )

    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

    yield f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""


def write_stream(stream):
    "write out the stream of the LLM's answer"
    with st.spinner("Thinking...", show_time=True):
        lock_llm()

        st.session_state["llm_answer"] = ""
        st.session_state["reasoning"] = ""

        # initialize an llm response in case interruption during reasoning
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "reasoning"
        ] += [st.session_state["reasoning"]]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "messages"
        ] += [
            {
                "role": "assistant",
                "content": "",
            }
        ]  # don't include time in chat history
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "times"
        ] += [
            f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
        ]

        if st.session_state["is_reasoning_model"]:
            with st.expander("Reasoning", expanded=True):
                container = st.empty()
                for chunk in stream:
                    st.session_state["reasoning"] += chunk
                    if "</think>" not in st.session_state["reasoning"]:
                        container.write(
                            f'<em>{st.session_state["reasoning"]}</em>',
                            unsafe_allow_html=True,
                        )

                        # add to reasoning history
                        st.session_state["chat_history"][
                            st.session_state["selected_chat_id"]
                        ]["reasoning"][-1] = st.session_state["reasoning"]
                    else:
                        break

        # normal LLM output
        container = st.empty()
        for chunk in stream:
            st.session_state["llm_answer"] += chunk
            container.write(st.session_state["llm_answer"], unsafe_allow_html=True)

            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "messages"
            ][-1] = {
                "role": "assistant",
                "content": st.session_state["llm_answer"].split("<br> <sub>")[0],
            }

            st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                "times"
            ][
                -1
            ] = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""

        unlock_llm()
