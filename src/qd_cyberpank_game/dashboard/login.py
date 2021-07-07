import streamlit as st


def login_callback():
    if st.session_state.login == 'root' and st.session_state.password == 'root':
        st.session_state.logged_user = 'root'
    else:
        st.session_state.logged_user = None


def logout_callback():
    st.session_state.logged_user = None


def login_form():
    with st.form(key='login_form'):
        st.text('Corporate information system')
        st.text_input('Login:', key='login')
        st.text_input('Password:', type='password', key='password')
        if st.form_submit_button('Login', on_click=login_callback):
            if not st.session_state.logged_user:
                st.error('Wrong login or password')


def logout_button():
    st.button('Logout', on_click=logout_callback)
