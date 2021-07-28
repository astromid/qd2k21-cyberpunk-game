import pandas as pd
import streamlit as st
from qd_cyberpank_game.dashboard.update_state import update_game_state
from qd_cyberpank_game.db import finish_cycle, make_auto_green_investment, make_next_cycle, reinit_game, make_transaction
from qd_cyberpank_game.db import update_investment_status, update_investment_multiplier
from qd_cyberpank_game.structures import Transaction
from qd_cyberpank_game.dashboard.stocks import stocks_block


def finish_cycle_callback():
    update_game_state(uid=st.session_state.user.uid)
    make_auto_green_investment(
        db_conn_str=st.session_state.db_conn_str,
        investments_df=st.session_state.investments,
        prev_investments_df=st.session_state.prev_investments,
        cycle=st.session_state.cycle,
        investments_table=st.session_state.db_schema['investments'],
    )
    update_game_state(uid=st.session_state.user.uid)
    finish_cycle(
        db_conn_str=st.session_state.db_conn_str,
        investments_df=st.session_state.investments,
        markets_df=st.session_state.markets,
        stocks_df=st.session_state.stocks,
        users_df=st.session_state.users,
        fund_speed=st.session_state.fund_speed,
        cycle=st.session_state.cycle,
        investments_table=st.session_state.db_schema['investments'],
        markets_table=st.session_state.db_schema['markets'],
        transactions_table=st.session_state.db_schema['transactions'],
        stocks_table=st.session_state.db_schema['stocks'],
    )
    make_next_cycle(st.session_state.db_conn_str, st.session_state.cycle, st.session_state.fund_speed_change, st.session_state.db_schema['cycles'])


def reinit_callback():
    reinit_game(
        db_conn_str=st.session_state.db_conn_str,
        users_df=st.session_state.users,
        markets_table=st.session_state.db_schema['markets'],
        stocks_table=st.session_state.db_schema['stocks'],
        transactions_table=st.session_state.db_schema['transactions'],
    )


def manual_transaction_callback():
    transaction = Transaction(
        from_=st.session_state.manual_transaction_from,
        to_=st.session_state.manual_transaction_to,
        amount=st.session_state.manual_transaction_amount,
        cycle=st.session_state.cycle,
    )
    make_transaction(st.session_state.db_conn_str, st.session_state.db_schema['transactions'], transaction)


def manual_multiplier_callback():
    uid = st.session_state.manual_multiplier_uid
    market = st.session_state.manual_multiplier_market
    multiplier = st.session_state.manual_multiplier
    investment_df = st.session_state.investments
    bid_ids = investment_df[(investment_df['uid'] == uid) & (investment_df['market'] == market)]['id'].tolist()
    for bid_id in bid_ids:
        update_investment_multiplier(
            st.session_state.db_conn_str,
            st.session_state.db_schema['investments'],
            bid_id,
            multiplier,
        )


def bid_check_callback():
    bid_id = st.session_state.bid_id
    status = 1 if st.session_state.bid_decision == 'Accept' else 0
    update_investment_status(st.session_state.db_conn_str, st.session_state.db_schema['investments'], bid_id=bid_id, status=status)


def root_dashboard():
    with st.sidebar:
        st.number_input('fund_speed', min_value=0.0, help='Fund speed', key='fund_speed_change', value=st.session_state.fund_speed)
        st.button('Закончить цикл', on_click=finish_cycle_callback)
        reinit_game = st.checkbox('Разрешить реинициализацию')
        if reinit_game:
            st.button('Реинициализация', on_click=reinit_callback)

    st.title('Административная панель')
    st.markdown(f'## Цикл: {st.session_state.cycle}')
    st.markdown(f'### Скорость инвестирования капитала: ${st.session_state.fund_speed / 1000000:.2f} млн. / мин')
    investments_df = st.session_state.investments
    users = st.session_state.users
    uid2name = {record['uid']: record['name'] for record in users[['uid', 'name']].to_dict('records')}
    stocks_block()
    with st.beta_expander(label='Одобрение заявок в SEC', expanded=True):
        pending_bids = investments_df[investments_df['status'] == -1].copy()
        pending_bids['corporation'] = pending_bids['uid'].map(uid2name)
        pending_bids = pending_bids.drop(['uid', 'timestamp_created', 'timestamp_approved', 'income', 'status'], axis=1)
        pending_bids = pending_bids[['id', 'corporation', 'market', 'amount', 'multiplier', 'cycle']]
        st.write('Заявки в ожидании:')
        st.dataframe(pending_bids)
        with st.form('bids_approving', clear_on_submit=True):
            st.selectbox('ID заявки', options=pending_bids['id'], key='bid_id')
            st.selectbox('Решение', options=['Accept', 'Reject'], key='bid_decision')
            st.form_submit_button('Отправить решение', on_click=bid_check_callback)
    with st.beta_expander(label='Ручное управление'):
        col1, col2, col3 = st.beta_columns([1, 1, 1])
        with col1:
            with st.form('transactions_form'):
                st.write('Создание транзакции')
                st.selectbox('From', options=users['uid'].tolist() + ['root'], key='manual_transaction_from')
                st.selectbox('To', options=users['uid'].tolist() + ['root'], key='manual_transaction_to')
                st.number_input('Amount', step=1.0, key='manual_transaction_amount')
                st.form_submit_button('Провести транзакцию', on_click=manual_transaction_callback)
        with col2:
            with st.form('multiplier_form'):
                st.write('Создание модификатора')
                st.selectbox('Игрок', options=users['uid'], key='manual_multiplier_uid')
                st.selectbox('Рынок', options=st.session_state.markets['name'], key='manual_multiplier_market')
                st.number_input('Множитель', min_value=0.0, key='manual_multiplier')
                st.form_submit_button('Установить модификатор', on_click=manual_multiplier_callback)
