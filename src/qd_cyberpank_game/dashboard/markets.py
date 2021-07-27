import math
from datetime import datetime
from typing import Optional

import altair as alt
import numpy as np
import pandas as pd
import pyecharts.options as opts
import streamlit as st
from pyecharts.charts import Graph
from pyecharts.commons.utils import JsCode
from qd_cyberpank_game.db import make_investment
from qd_cyberpank_game.structures import InvestmentBid, ThemeColors
from streamlit_echarts import st_pyecharts

TOOLTIP_JS_CODE = ''.join([
    'function(params){',
    'var bulletItem = (field, value) => ',
    "'<p>' + params.marker + ' ' + field + ' ' + '<b>' + value + '</b></p>';",
    "let tip = bulletItem('Инвестировано', params.data.amount);",
    "tip += bulletItem('Прибыль', params.data.income);",
    "tip += bulletItem('Прибыль', params.data.profit);",
    "tip += bulletItem('Множитель x', params.data.multiplier);",
    'return tip;',
    '}',
])


def get_node_size_px(capacity, min_capacity) -> float:
    return 70 * math.log(capacity / min_capacity, 5)


def get_node_color(investment: float, income: float) -> str:
    if investment == 0:
        return ThemeColors.GRAY.value
    elif income > 0:
        return ThemeColors.GREEN.value
    elif income < 0:
        return ThemeColors.RED.value
    else:
        return ThemeColors.BLUE.value


def make_markets_graph(markets_df: pd.DataFrame, investments_df: pd.DataFrame, home_market: Optional[str]) -> Graph:
    approved_investments = investments_df[investments_df['status'] == 1]
    # absolute minimum capacity
    min_capacity = markets_df['min_capacity'].min()
    graph = Graph()
    graph_nodes = [{
        'name': market['name'],
        'symbolSize': get_node_size_px(market['capacity'], 10000),
    } for market in markets_df.to_dict('records')]
    graph_links = [{
        'source': link['name'],
        'target': link['value'],
    } for link in markets_df.melt(id_vars='name', value_vars=['link1', 'link2']).dropna().to_dict('records')]
    for node in graph_nodes:
        node_investment = approved_investments[approved_investments['market'] == node['name']]
        if not node_investment.empty:
            node_investment = node_investment.to_dict('records')[0]
            node['amount'] = node_investment['amount']
            node['income'] = node_investment['income']
            node['profit'] = f"{node_investment['profit']:.2%}"
            node['multiplier'] = 1
        else:
            node['amount'] = 0
            node['income'] = 0
            node['profit'] = f'{0:.2%}'
            node['multiplier'] = 1
        node['symbol'] = 'roundRect' if node['name'] == home_market else 'circle'
        node['itemStyle'] = {'color': get_node_color(node['amount'], node['income'])}
    
    unlocked_markets = [home_market]
    for link in graph_links:
        for node in graph_nodes:
            if node['name'] == link['source']:
                source_color = node['itemStyle']['color']
            if node['name'] == link['target']:
                target_color = node['itemStyle']['color']

        if source_color == ThemeColors.GREEN.value or target_color == ThemeColors.GREEN.value:
            link_color = ThemeColors.GREEN.value
            unlocked_markets.append(link['source'])
            unlocked_markets.append(link['target'])
        else:
            link_color = ThemeColors.GRAY.value
        link['lineStyle'] = {'color': link_color}

    st.session_state.unlocked_markets = np.unique(unlocked_markets).tolist()
    graph.add(
        'Markets',
        repulsion=2000,
        edge_length=130,
        edge_symbol=['arrow', 'arrow'],
        edge_symbol_size=8,
        label_opts=opts.LabelOpts(position='inside'),
        tooltip_opts=opts.TooltipOpts(
            formatter=JsCode(TOOLTIP_JS_CODE),
            border_width=1,
        ),
        nodes=graph_nodes,
        links=graph_links,
        linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.9, curve=0.2),
    )
    return graph


def markets_status():
    markets_df = st.session_state.markets
    prev_investments_df = st.session_state.prev_investments
    prev_investments_df['profit'] = prev_investments_df['income'] / prev_investments_df['amount']
    graph = make_markets_graph(markets_df=markets_df, investments_df=prev_investments_df, home_market=st.session_state.user.home_market)
    col1, col2 = st.beta_columns([1, 1])
    with col1:
        st.markdown('<p style="text-align: center;"> Состояние графа рынков в прошлом периоде </p>', unsafe_allow_html=True)
        st_pyecharts(graph, height='600px')
    with col2:
        st.markdown('<p style="text-align: center;"> Графики инвестиций по рынкам за прошлый период </p>', unsafe_allow_html=True)
        investments_nonzero_df = prev_investments_df[prev_investments_df['amount'] != 0]
        if investments_nonzero_df.empty:
            st.markdown('<p style="text-align: center;"> В прошлом периоде инвестиций не было </p>', unsafe_allow_html=True)
        else:
            st.altair_chart(alt.Chart(investments_nonzero_df).mark_bar().encode(
                    x='market',
                    y='amount',
                    color=alt.condition(alt.datum.profit > 0, alt.value(ThemeColors.GREEN.value), alt.value(ThemeColors.RED.value)),
                ).properties(width=600, height=400))
            st.altair_chart(alt.Chart(investments_nonzero_df).mark_bar().encode(
                    x='market',
                    y='profit',
                    color=alt.condition(alt.datum.profit > 0, alt.value(ThemeColors.GREEN.value), alt.value(ThemeColors.RED.value)),
                ).properties(width=600, height=400))
    st.markdown(f'### Вложения {st.session_state.user.name} Corporation за предыдущий период')
    st.dataframe(prev_investments_df.drop('uid', axis=1))


def markets_investment_form():
    markets_df = st.session_state.markets
    investments_df = st.session_state.investments

    frozen_markets = []
    if not investments_df.empty:
        frozen_markets = investments_df.loc[investments_df['status'].isin([-1, 1]), 'market'].tolist()
    st.session_state.frozen_markets = frozen_markets
    with st.form(key='investments_form'):
        st.markdown('## Инвестиционная форма SEC CP/20-77 ')
        st.markdown('### Открытые для инвестирования рынки:')
        for market in markets_df['name'].values:
            if market not in st.session_state.unlocked_markets:
                continue

            col1, col2 = st.beta_columns([1, 1])
            with col1:
                st.number_input(label=f'Инвестиции в {market}', key=f'investment_{market}', min_value=0.0)
            with col2:
                bid_status = None
                if not investments_df.empty:    
                    bid = investments_df.loc[investments_df['market'] == market, 'status']
                    if not bid.empty:
                        bid_status = bid.item()

                if bid_status is None:
                    status_str = f"<span style='color: {ThemeColors.GRAY.value};'> NOT AVAILABLE </span>"
                elif bid_status == -1:
                    status_str = f"<span style='color: {ThemeColors.BLUE.value};'> PENDING </span>"
                elif bid_status == 1:
                    status_str = f"<span style='color: {ThemeColors.GREEN.value};'> ACCEPTED </span>"
                else:
                    status_str = f"<span style='color: {ThemeColors.RED.value};'> REJECTED </span>"
                st.markdown(f'## <br /><p> Статус: {status_str} </p>', unsafe_allow_html=True)
        st.form_submit_button(label='Отправить заявку в SEC', on_click=markets_investment_callback)
        if st.session_state.frozen_markets:
            st.warning(f"На следующие рынки уже поданы заявки: {', '.join(frozen_markets)}. Эти заявки не будут обновлены.")
            rejected_bids = getattr(st.session_state, 'rejected_bids', None)
            if rejected_bids:
                st.warning(f"Заявки на следующие рынки были отклонены из-за недостаточного баланса: {', '.join(rejected_bids)}")
    st.markdown(f'### Открытые инвестиционные заявки:')
    st.dataframe(investments_df.drop('uid', axis=1))


def markets_investment_callback():
    investment_bids: list[InvestmentBid] = []
    bids_balance = 0
    rejected_bids = []
    for market in st.session_state.unlocked_markets:
        inv_amount = getattr(st.session_state, f'investment_{market}')
        if inv_amount != 0 and market not in st.session_state.frozen_markets:
            bids_balance += inv_amount
            if bids_balance <= st.session_state.balance:
                investment_bids.append(InvestmentBid(
                    id=None,
                    uid=st.session_state.user.uid,
                    market=market,
                    amount=inv_amount,
                    timestamp_created=datetime.now(),
                    timestamp_approved=None,
                    status=-1,
                    cycle=st.session_state.cycle,
                    income=None,
                ))
            else:
                rejected_bids.append(market)
    st.session_state.rejected_bids = rejected_bids
    for investment_bid in investment_bids:
        make_investment(st.session_state.db_conn_str, st.session_state.db_schema['investments'], investment_bid)
