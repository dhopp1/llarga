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
