import streamlit as st

from qd_cyberpank_game.dashboard.login import login_form, logout_button
from qd_cyberpank_game.dashboard.root import root_dashboard
from qd_cyberpank_game.dashboard.update_state import update_game_state, update_state_callback
from qd_cyberpank_game.dashboard.user import user_dashboard
from qd_cyberpank_game.db import read_db_schema

DB_CONN_STR = f"mysql+pymysql://{st.secrets['db_username']}:{st.secrets['db_password']}@localhost:3306/game1"
INITIAL_STATE = {
    'user': None,
    'db_conn_str': DB_CONN_STR,
    'db_schema': read_db_schema(DB_CONN_STR),
}


def init_state():
    for state_key, init_value in INITIAL_STATE.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = init_value


def dashboard():
    if st.session_state.user is None:
        st.markdown('## Пожалуйста, авторизуйтесь для доступа к операционной информации.')
        with st.sidebar:
            login_form()
    else:
        with st.sidebar:
            logout_button()
            st.button('Обновить данные', on_click=update_state_callback)
        
        update_game_state(uid=st.session_state.user.uid)
        if st.session_state.user.uid == 'root':
            root_dashboard()
        else:
            user_dashboard()


if __name__ == '__main__':
    init_state()
    title = f'CP 2.0.20: {st.session_state.user.name}' if st.session_state.user else 'CP 2.0.20: Авторизация'
    st.set_page_config(page_title=title, layout='wide')
    dashboard()
