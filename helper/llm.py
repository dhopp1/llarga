from datetime import datetime
from openai import OpenAI
import streamlit as st
from streamlit_server_state import server_state

from helper.user_management import lock_llm, unlock_llm


def gen_llm_response(query, messages_input=[]):
    """Create the data required for an LLM call"""
    messages = messages_input.copy()
    initial_prompt = messages[-1]["content"]

    # llm model name
    llm_model_name = (
        st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "model_name",
        ]
        .values[0]
    )

    client = OpenAI(
        api_key=st.session_state["llm_api_key"],
        base_url=st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "llm_url",
        ]
        .values[0],
    )

    # is openrouter reasoning
    st.session_state["openrouter_reasoning"] = st.session_state[
        "is_reasoning_model"
    ] and "openrouter" in (
        st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "llm_url",
        ]
        .values[0]
    )

    # modifying prompt to remove time
    messages[-1]["content"] = messages[-1]["content"].split("<br> <sub>")[0]

    # adding RAG if necessary
    context_length = int(
        st.session_state["llm_info"]
        .loc[
            lambda x: x["name"] == st.session_state["selected_llm"],
            "context_length",
        ]
        .values[0]
    )
    chunk_size = int(
        st.session_state["settings"]
        .loc[lambda x: x["field"] == "chunk_size", "value"]
        .values[0]
    )
    top_n = int(
        context_length
        / chunk_size
        * float(
            st.session_state["settings"]
            .loc[lambda x: x["field"] == "context_window_rag_ratio", "value"]
            .values[0]
        )
    )

    if st.session_state["selected_corpus"] != "No corpus":
        if not (
            any(
                sub in messages[-1]["content"]
                for sub in ["Given this chat history", "Given this past exchange"]
            )
        ):  # don't run for naming the chat
            # logic for a condensed standalone query
            if (len(messages) > 2) and (
                st.session_state["settings"]
                .loc[lambda x: x["field"] == "use_condensed_lvs_query", "value"]
                .values[0]
                == "1"
            ):  # 2 = 1 system, 1 user prompt
                condensed_messages = messages.copy()
                condensed_messages[-1][
                    "content"
                ] = f"Given this past exchange, edit this question so that it stands alone in terms of context. Return only the reformulated question, nothing else. Here is the question: '{condensed_messages[-1]['content']}'"

                condense_response = client.chat.completions.create(
                    model=llm_model_name,
                    temperature=0.0,
                    max_tokens=st.session_state["max_tokens"],
                    messages=condensed_messages.copy(),
                )
                try:
                    condensed_query = condense_response.choices[
                        0
                    ].message.content.split("</think>")[1]
                except:
                    condensed_query = condense_response.choices[0].message.content
            else:
                condensed_query = messages[-1]["content"]

            text_ids = list(
                st.session_state["display_metadata"]
                .loc[lambda x: x["Include in queries"] == True, "text_id"]
                .values
            )
            lvs_context = server_state["lvs_corpora"][
                st.session_state["selected_corpus_realname"]
            ].get_top_n(
                condensed_query,
                top_n=top_n,
                distance_metric="cosine",
                text_ids=text_ids,
            )
            st.session_state["latest_chunk_ids"] = lvs_context["chunk_ids"]
            messages[-1][
                "content"
            ] = f"""{initial_prompt} \n\n {lvs_context["response"]}"""

    # final llm response
    if st.session_state["openrouter_reasoning"]:
        response = client.chat.completions.create(
            model=llm_model_name,
            temperature=st.session_state["temperature"],
            max_tokens=st.session_state["max_tokens"],
            messages=messages.copy(),
            reasoning_effort="medium",
            stream=True,
        )
    else:
        response = client.chat.completions.create(
            model=llm_model_name,
            temperature=st.session_state["temperature"],
            max_tokens=st.session_state["max_tokens"],
            messages=messages.copy(),
            stream=True,
        )

    messages[-1]["content"] = initial_prompt

    n_fail = 0  # for openrouter reasoning
    first_token = 0
    for chunk in response:
        first_token += 1
        # openrouter reasoning
        if st.session_state["openrouter_reasoning"]:
            try:
                if chunk.choices[0].delta.reasoning is not None:
                    yield chunk.choices[0].delta.reasoning
                else:
                    if first_token != 1:
                        n_fail += 1
                        if n_fail == 1:
                            yield "</think>" + chunk.choices[0].delta.content
                        else:
                            if chunk.choices[0].delta.content is not None:
                                yield chunk.choices[0].delta.content
            except:
                pass
        else:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    yield f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""


def write_stream(stream):
    "write out the stream of the LLM's answer"
    with st.spinner("Thinking...", show_time=True):
        if (
            ".gguf"
            in st.session_state["llm_info"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_llm"],
                "model_name",
            ]
            .values[0]
        ) and (
            st.session_state["settings"]
            .loc[lambda x: x["field"] == "manage_llama_cpp", "value"]
            .values[0]
            == "1"
        ):
            lock_llm()

        st.session_state["llm_answer"] = ""
        st.session_state["reasoning"] = ""

        # initialize an llm response in case interruption during reasoning
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "reasoning"
        ] += [st.session_state["reasoning"]]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "corpus"
        ] += [st.session_state["selected_corpus"]]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "chunk_ids"
        ] += [[]]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "selected_llm"
        ] += [st.session_state["selected_llm"]]
        st.session_state["chat_history"][st.session_state["selected_chat_id"]][
            "model_style"
        ] += [st.session_state["temperature_string"]]
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

                        # add to chunk_ids history
                        if (
                            len(
                                st.session_state["chat_history"][
                                    st.session_state["selected_chat_id"]
                                ]["chunk_ids"][-1]
                            )
                            == 0
                        ) and (st.session_state["selected_corpus"] != "No corpus"):
                            st.session_state["chat_history"][
                                st.session_state["selected_chat_id"]
                            ]["chunk_ids"][-1] = st.session_state["latest_chunk_ids"]
                    else:
                        if st.session_state[
                            "openrouter_reasoning"
                        ]:  # have to maintain first non-reasoning chunk
                            st.session_state["llm_answer"] += chunk.split("</think>")[1]
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

            # add to chunk_ids history
            if (
                len(
                    st.session_state["chat_history"][
                        st.session_state["selected_chat_id"]
                    ]["chunk_ids"][-1]
                )
                == 0
            ) and (st.session_state["selected_corpus"] != "No corpus"):
                st.session_state["chat_history"][st.session_state["selected_chat_id"]][
                    "chunk_ids"
                ][-1] = st.session_state["latest_chunk_ids"]

        if (
            ".gguf"
            in st.session_state["llm_info"]
            .loc[
                lambda x: x["name"] == st.session_state["selected_llm"],
                "model_name",
            ]
            .values[0]
        ) and (
            st.session_state["settings"]
            .loc[lambda x: x["field"] == "manage_llama_cpp", "value"]
            .values[0]
            == "1"
        ):
            unlock_llm()
