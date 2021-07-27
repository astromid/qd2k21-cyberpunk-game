import pandas as pd
import streamlit as st
from qd_cyberpank_game.dashboard.markets import markets_investment_form, markets_status
from qd_cyberpank_game.dashboard.stocks import stocks_block
from qd_cyberpank_game.structures import ThemeColors


def user_dashboard():
    user = st.session_state.user
    cycle = st.session_state.cycle
    transactions_df = st.session_state.transactions
    in_transactions = transactions_df[transactions_df['to_'] == user.uid]
    out_transactions = transactions_df[transactions_df['from_'] == user.uid]
    balance = in_transactions['amount'].sum() - out_transactions['amount'].sum()
    cycle_income = in_transactions.loc[in_transactions['cycle'] == cycle - 1, 'amount'].sum()
    cycle_outcome = out_transactions.loc[out_transactions['cycle'] == cycle - 1, 'amount'].sum()
    cycle_balance = cycle_income - cycle_outcome
    if cycle_balance > 0:
        cycle_balance_str = f"<span style='color: {ThemeColors.GREEN.value};'>+{cycle_balance:,}</span>:atom_symbol:"
    elif cycle_balance < 0:
        cycle_balance_str = f"<span style='color: {ThemeColors.RED.value};'>{cycle_balance:,}</span>:atom_symbol:"
    else:
        cycle_balance_str = f"<span style='color: {ThemeColors.GRAY.value};'>+{cycle_balance:,}</span>:atom_symbol:"
    st.title(f'{st.session_state.user.name} Corporation')
    st.markdown(f'# Система корпоративного управления CP 2.0.20')
    st.markdown(f'## Цикл: {cycle}')
    st.markdown(f'## Текущий баланс: {balance:,}:atom_symbol: ({cycle_balance_str})', unsafe_allow_html=True)
    stocks_block()
    markets_status()
    markets_investment_form()
