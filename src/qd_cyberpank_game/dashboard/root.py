import pandas as pd
import streamlit as st
from qd_cyberpank_game.db import make_next_cycle


def finish_cycle_callback():
    calculate_markets_state()
    make_transactions()
    make_next_cycle(st.session_state.db_conn_str, st.session_state.cycle, st.session_state.db_schema['cycles'])


def root_dashboard():
    with st.sidebar:
        st.button('Закончить цикл', on_click=finish_cycle_callback)
    st.title('Административная панель')
    st.markdown(f'## Текущий цикл: {st.session_state.cycle}')
    st.dataframe(st.session_state.markets)
    st.dataframe(st.session_state.transactions, width=900)
    st.dataframe(st.session_state.investments)
