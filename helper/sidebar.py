import pandas as pd
import streamlit as st


def sidebar_llm_dropdown():
    if "llm_info" not in st.session_state:
        st.session_state["llm_info"] = pd.read_csv("metadata/llm_list.csv")
        st.session_state["llm_dropdown_options"] = list(
            st.session_state["llm_info"].loc[lambda x: x["display"] == 1, "name"].values
        )

    with st.sidebar:
        st.session_state["selected_llm"] = st.selectbox(
            "Select LLM",
            options=st.session_state["llm_dropdown_options"],
            index=(
                0
                if "selected_llm" not in st.session_state
                else st.session_state["llm_dropdown_options"].index(
                    st.session_state["selected_llm"]
                )
            ),
            help="Which LLM to use. Those ending in `(private)` do not leave our local system, those ending in `(cloud)` will be sent to a cloud provider via API. The latter should not be used for sensitive information.",
        )


def sidebar_llm_api_key():
    with st.sidebar:
        with st.expander("LLM API key"):
            st.session_state["llm_api_key_user"] = st.text_input(
                "Paste key here",
                help="Paste your API key for the cloud LLM provider if availalble.",
            )

        if "llm_api_key" not in st.session_state:
            st.session_state["llm_api_key"] = (
                st.session_state["llm_info"]
                .loc[lambda x: x["name"] == st.session_state["selected_llm"], "api_key"]
                .values[0]
            )

        # use the user's if provided
        if st.session_state["llm_api_key_user"] != "":
            st.session_state["llm_api_key"] = st.session_state["llm_api_key_user"]
        else:
            st.session_state["llm_api_key"] = (
                st.session_state["llm_info"]
                .loc[lambda x: x["name"] == st.session_state["selected_llm"], "api_key"]
                .values[0]
            )


def sidebar_temperature_dropdown():
    with st.sidebar:
        temp_options = [
            "Most precise",
            "Precise",
            "Balanced",
            "Creative",
            "Most creative",
        ]
        st.session_state["temperature_string"] = st.selectbox(
            "Model style",
            options=temp_options,
            index=(
                0
                if "temperature_string" not in st.session_state
                else temp_options.index(st.session_state["temperature_string"])
            ),
            help="""
### Most precise
The LLM will be the most predictable and consistent. For anything fact-based, use this setting.
### Precise
The LLM is still mostly precise, but has slightly more freedem in creating its answers.
### Balanced
The LLM is a mixture of creative and precise.
### Creative
The LLM has quite a bit of freedom in creating its answers, which may be inconsistent from question to question.
### Most creative
The LLM has maximum creativity and freedom.
""",
        )

        st.session_state["temperature"] = dict(
            zip(
                ["Most precise", "Precise", "Balanced", "Creative", "Most creative"],
                [0.0, 0.15, 0.4, 0.7, 1.0],
            )
        )[st.session_state["temperature_string"]]
