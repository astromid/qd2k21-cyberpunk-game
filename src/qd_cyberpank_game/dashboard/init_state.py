import streamlit as st

INIT_STATE = {
    'logged_user': None,
}


def init_state():
    for state_key, init_value in INIT_STATE.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = init_value
