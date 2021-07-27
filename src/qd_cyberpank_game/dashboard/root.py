import pandas as pd
import streamlit as st
from qd_cyberpank_game.db import calculate_markets_state, make_next_cycle


def finish_cycle_callback():
    calculate_markets_state(
        db_conn_str=st.session_state.db_conn_str,
        investments_df=st.session_state.investments,
        markets_df=st.session_state.markets,
        fund_speed=st.session_state.fund_speed,
        cycle=st.session_state.cycle,
        investments_table=st.session_state.db_schema['investments'],
        markets_table=st.session_state.db_schema['markets'],
        transactions_table=st.session_state.db_schema['transactions'],
    )
    make_next_cycle(st.session_state.db_conn_str, st.session_state.cycle, st.session_state.fund_speed_change, st.session_state.db_schema['cycles'])


def root_dashboard():
    with st.sidebar:
        st.number_input('fund_speed', min_value=0.0, help='Fund speed', key='fund_speed_change', value=st.session_state.fund_speed)
        st.button('Закончить цикл', on_click=finish_cycle_callback)
    st.title('Административная панель')
    st.markdown(f'## Текущий цикл: {st.session_state.cycle}')
    st.dataframe(st.session_state.markets)
    st.dataframe(st.session_state.transactions, width=900)
    st.dataframe(st.session_state.investments)
