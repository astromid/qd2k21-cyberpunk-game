import streamlit as st
import qd_cyberpank_game.db as db


def update_game_state(uid: str) -> None:
    db_conn_str = st.session_state.db_conn_str
    db_schema = st.session_state.db_schema
    placeholder = st.empty()
    with placeholder.beta_container():
        st.write('Загрузка актуальных данных...')
        progressbar = st.progress(0)
        st.session_state.cycle, st.session_state.fund_speed = db.get_current_cycle(db_conn_str, db_schema['cycles'])
        progressbar.progress(10)
        st.session_state.users = db.get_users(db_conn_str, db_schema['users'])
        progressbar.progress(20)
        st.session_state.markets = db.get_markets(db_conn_str, db_schema['markets'])
        progressbar.progress(30)
        st.session_state.transactions = db.get_transactions(db_conn_str, uid, db_schema['transactions'])
        progressbar.progress(40)
        st.session_state.prev_investments = db.get_cycle_investments(db_conn_str, uid, st.session_state.cycle - 1, db_schema['investments'])
        progressbar.progress(50)
        st.session_state.investments = db.get_cycle_investments(db_conn_str, uid, st.session_state.cycle, db_schema['investments'])
        progressbar.progress(60)
        st.session_state.stocks = db.get_stocks(db_conn_str, db_schema['stocks'])
        progressbar.progress(100)
    placeholder.empty()


def update_state_callback():
    update_game_state(uid=st.session_state.user.uid)
