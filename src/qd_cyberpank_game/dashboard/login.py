import streamlit as st

from qd_cyberpank_game.db import auth


def login_callback():
    st.session_state.user = auth(
        st.session_state.login,
        st.session_state.password,
        st.session_state.db_conn_str,
        st.session_state.db_schema['users'],
    )


def logout_callback():
    st.session_state.user = None


def login_form():
    with st.form(key='login_form'):
        st.text('Корпоративная система v2.0.77')
        st.text_input('Логин:', key='login')
        st.text_input('Пароль:', type='password', key='password')
        if st.form_submit_button('Войти', on_click=login_callback):
            if not st.session_state.user:
                st.error('Неверный логин или пароль')


def logout_button():
    st.button('Выход из системы', on_click=logout_callback)
