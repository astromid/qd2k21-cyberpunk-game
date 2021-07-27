from typing import Tuple
import pandas as pd
import streamlit as st
from qd_cyberpank_game.dashboard.markets import markets_investment_form, markets_status
from qd_cyberpank_game.dashboard.stocks import stocks_block
from qd_cyberpank_game.structures import ThemeColors, User


def get_balance(transactions_df: pd.DataFrame, user: User, cycle: int) -> Tuple[float, float]:
    in_transactions = transactions_df[transactions_df['to_'] == user.uid]
    out_transactions = transactions_df[transactions_df['from_'] == user.uid]
    balance = in_transactions['amount'].sum() - out_transactions['amount'].sum()

    cycle_income = in_transactions.loc[in_transactions['cycle'] == cycle - 1, 'amount'].sum()
    cycle_outcome = out_transactions.loc[out_transactions['cycle'] == cycle - 1, 'amount'].sum()
    cycle_balance = cycle_income - cycle_outcome
    return balance, cycle_balance


def make_balance_str(balance, cycle_balance, frozen_balance) -> str:
    if cycle_balance > 0:
        cycle_balance_str = f"<span style='color: {ThemeColors.GREEN.value};'>+{cycle_balance:,}</span>:atom_symbol:"
    elif cycle_balance < 0:
        cycle_balance_str = f"<span style='color: {ThemeColors.RED.value};'>{cycle_balance:,}</span>:atom_symbol:"
    else:
        cycle_balance_str = f"<span style='color: {ThemeColors.GRAY.value};'>+{cycle_balance:,}</span>:atom_symbol:"
    frozen_balace_str = f"<span style='color: {ThemeColors.GRAY.value};'>-{frozen_balance:,}</span>:atom_symbol: инвестировано"
    return f'## Баланс: {balance:,}:atom_symbol: ({cycle_balance_str}) / ({frozen_balace_str})'


def user_dashboard():
    user = st.session_state.user
    cycle = st.session_state.cycle
    transactions_df = st.session_state.transactions
    investments_df = st.session_state.investments
    if not investments_df.empty:
        active_bids = investments_df[investments_df['status'].isin([-1, 1])]
        frozen_balance = active_bids['amount'].sum()
    else:
        frozen_balance = 0

    st.session_state.balance, cycle_balance = get_balance(transactions_df, user, cycle)
    st.session_state.balance -= frozen_balance
    
    st.title(f'{st.session_state.user.name} Corporation')
    st.markdown(f'# Система корпоративного управления CP 2.0.20')
    st.markdown(f'## Цикл: {cycle}')
    st.markdown(make_balance_str(st.session_state.balance, cycle_balance, frozen_balance), unsafe_allow_html=True)
    stocks_block()
    markets_status()
    markets_investment_form()
