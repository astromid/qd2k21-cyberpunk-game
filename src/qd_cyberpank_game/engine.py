from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


def calculate_investments(investments_df: pd.DataFrame, markets_df: pd.DataFrame, fund_speed: float):
    approved_invest_bids = investments_df[(investments_df['status'] == 1) & investments_df['income'].isnull()].copy()
    if approved_invest_bids.empty:
        return None

    approved_invest_bids['duration'] = datetime.now() - approved_invest_bids['timestamp_approved']
    approved_invest_bids['funded_amount'] = fund_speed * approved_invest_bids['duration'].dt.seconds / 60
    approved_invest_bids['funded_amount'] = approved_invest_bids['multiplier'] * approved_invest_bids[['funded_amount', 'amount']].min(axis=1)

    markets = approved_invest_bids['market'].unique().tolist()
    market_incomes = []
    new_market_capacities = {}
    for market in markets:
        market_bids = approved_invest_bids[approved_invest_bids['market'] == market]
        bid_ids = market_bids['id'].tolist()
        uids = market_bids['uid'].tolist()
        funded_amounts = market_bids['funded_amount'].values
        market_capacity = markets_df.loc[markets_df['name'] == market, 'capacity'].item()
        min_market_capacity = markets_df.loc[markets_df['name'] == market, 'min_capacity'].item()
        incomes, new_market_capacity = calculate_market(funded_amounts, market_capacity, min_market_capacity)
        for bid_id, uid, income in zip(bid_ids, uids, incomes):
            market_incomes.append({
                'bid_id': bid_id,
                'uid': uid,
                'market': market,
                'income': income,
            })
        new_market_capacities[market] = new_market_capacity
    return market_incomes, new_market_capacities


def calculate_market(x: np.ndarray, capacity: float, min_capacity: float) -> Tuple[np.ndarray, float]:
    p = x / x.sum()
    p[p == 1] -= 1e-12
    y = (1 - np.square(p).sum()) / (1 - p) * x
    incomes = np.minimum(y - x, capacity)
    jackpot = x.sum() / 2
    new_capacity = np.maximum(capacity + jackpot - incomes.max(), min_capacity)
    return incomes, new_capacity


def generate_stocks(market_incomes: Optional[list[Dict[str, Any]]], stocks_df: pd.DataFrame, users_df: pd.DataFrame, cycle: int) -> pd.DataFrame:
    xs = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
    ticket_incomes = {}
    if market_incomes is None:
        ticket_incomes = {ticket: 0 for ticket in users_df['ticket']}
    else:
        for market_income in market_incomes:
            ticket = users_df.loc[users_df['uid'] == market_income['uid'], 'ticket'].item()
            if ticket not in ticket_incomes:
                ticket_incomes[ticket] = market_income['income']
            else:
                ticket_incomes[ticket] += market_income['income']
    stocks_df = stocks_df.sort_values('cycle')
    last_price = stocks_df.groupby('ticket')['price'].last().to_dict()
    partial_stocks_df = []
    for ticket, income in ticket_incomes.items():
        inner_points = np.sort(np.random.rand(4))
        inner_points = np.insert(inner_points, 0, 0)
        inner_points = np.insert(inner_points, 5, 1)
        deltas = np.diff(inner_points)
        income_rel = income / 5000000
        stocks_points = 5 * (income_rel * deltas + np.random.normal(0, 1, size=5))
        partial_stock_df = pd.DataFrame({'cycle': xs + cycle})
        partial_stock_df['ticket'] = ticket
        partial_stock_df['price'] = stocks_points + last_price[ticket]
        partial_stocks_df.append(partial_stock_df)
    return pd.concat(partial_stocks_df)
