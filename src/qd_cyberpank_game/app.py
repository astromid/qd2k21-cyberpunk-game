import time

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from pyecharts import options as opts
from pyecharts.charts import Graph
from pyecharts.commons.utils import JsCode
from streamlit_echarts import st_pyecharts

from qd_cyberpank_game.dashboard.init_state import init_state
from qd_cyberpank_game.dashboard.login import login_form, logout_button

BLUE_COLOR = '#5470c6'
RED_COLOR = '#ee6666'
GREEN_COLOR = '#91cc75'


def sidebar():
    with st.sidebar:
        if not st.session_state.logged_user:
            login_form()
        else:
            logout_button()
            st.write('Latest corp news:')
            st.markdown("""
                - bla
                - bla bla
                - bla bla bla
            """)


def stocks_block():
    data = pd.DataFrame({
        'cycle': np.arange(1, 20),
        'CRP_A': np.random.normal(3.0, 1.5, 19),
        'CRP_B': np.random.normal(2.0, 1.0, 19),
        'CRP_C': np.random.normal(1.5, 0.67, 19),
        'CRP_D': np.random.normal(1.0, 0.33, 19),
    })
    long_data = data.melt('cycle', var_name='symbol', value_name='price')
    with st.beta_expander('Stocks chart', expanded=True):
        col1, col2 = st.beta_columns([2, 1])
        with col1:
            nearest = alt.selection(type='single', nearest=True, on='mouseover', fields=['cycle'], empty='none')
            line = alt.Chart(long_data).mark_line(point=True).encode(x='cycle:Q', y='price:Q', color='symbol:N', strokeDash='symbol')
            selectors = alt.Chart(long_data).mark_point().encode(x='cycle:Q', opacity=alt.value(0)).add_selection(nearest)
            points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
            text = line.mark_text(align='left', dx=5, dy=-5).encode(text=alt.condition(nearest, 'price:Q', alt.value(' ')))
            rules = alt.Chart(long_data).mark_rule(color='gray').encode(x='cycle:Q').transform_filter(nearest)
            layer = alt.layer(line, selectors, points, rules, text).properties(width=900, height=450).interactive()
            st.altair_chart(layer)
        with col2:
            st.write(data)


def expansion_block():
    data = pd.DataFrame({
        'market': ['IT', 'Medicine', 'Cybersecurity', 'Argotech', 'Army'],
        'investments': (100000, 33000, 10000, 167000, 120000) * np.random.rand(5),
        'income': (10000, -20000, 7000, -34000, 27000) * np.random.rand(5),
    })
    data['profit'] = data['income'] / data['investments'] * 100
    with st.beta_expander('Markets expansion'):
        st.write('ALL YOUR BASE ARE BELONG TO US')
        col1, col2 = st.beta_columns([1, 1])
        with col1:
            st.altair_chart(alt.Chart(data).mark_bar().encode(
                x='market',
                y='investments',
                color=alt.condition(alt.datum.profit > 0, alt.value(GREEN_COLOR), alt.value(RED_COLOR)),
            ).properties(width=600, height=400))
        with col2:
            st.altair_chart(alt.Chart(data).mark_bar().encode(
                x='market',
                y='profit',
                color=alt.condition(alt.datum.profit > 0, alt.value(GREEN_COLOR), alt.value(RED_COLOR)),
            ).properties(width=600, height=400))
        st.write(data)


def market_graph():
    graph = Graph(opts.InitOpts(
        animation_opts=opts.AnimationOpts(animation_duration_update=2000, animation_easing_update='quinticInOut'),
    ))
    graph.add(
        'Markets',
        layout='circular',
        symbol_size=120,
        edge_symbol=['circle', 'arrow'],
        edge_symbol_size=[4, 10],
        label_opts=opts.LabelOpts(position='inside'),
        tooltip_opts=opts.TooltipOpts(
            formatter=JsCode("function(params){var bulletItem = (field, value) => '<p>' + params.marker + ' ' + field + ' ' + '<b>' + value + '</b></p>';let tip = bulletItem('Investment', params.data.investment);tip += bulletItem('Returns', params.data.returns);tip += bulletItem('Profit', params.data.profit);return tip;}"),
            border_width=1,
        ),
        nodes=[
            {'name': 'IT', 'investment': 10000, 'returns': 5000, 'profit': '-50%', 'itemStyle': {'color': RED_COLOR}},
            {'name': 'Medicine', 'itemStyle': {'color': GREEN_COLOR}},
            {'name': 'Cybersecurity', 'itemStyle': {'color': BLUE_COLOR}},
            {'name': 'Argotech', 'itemStyle': {'color': BLUE_COLOR}},
            {'name': 'Army', 'itemStyle': {'color': BLUE_COLOR}},
        ],
        links=[
            {'source': 'IT', 'target': 'Medicine', 'linkage': 0.99},
            {'source': 'IT', 'target': 'Cybersecurity', 'linkage': 0.01},
            {'source': 'Argotech', 'target': 'Army', 'linkage': 0.87},
            {'source': 'Medicine', 'target': 'Army', 'linkage': -0.7},
            {'source': 'Cybersecurity', 'target': 'Army', 'linkage': 0.7},
        ],
        linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.9, curve=0.2)
    )
    col1, col2 = st.beta_columns([2, 1])
    with col1:
        st_pyecharts(graph, height='600px')
    with col2:
        with st.form(key='investment_form'):
            st.number_input(label='IT investment')
            st.number_input(label='Medicine investment')
            st.number_input(label='Argotech investment')
            st.number_input(label='Cybersecurity investment')
            st.number_input(label='Army investment')
            st.form_submit_button()


def main_panel():
    if st.session_state.logged_user:
        placeholder = st.empty()
        with placeholder.beta_container():
            st.write('Loading actual data...')
            my_bar = st.progress(0)
            for pct in range(100):
                time.sleep(0.01)
                my_bar.progress(pct + 1)
        placeholder.empty()

        balance = 50_000_000
        prev_balance = 49_000_000
        delta = balance - prev_balance
        if delta > 0:
            delta_str = f"<span style='color: {GREEN_COLOR};'>+${delta}</span>"
        else:
            delta_str = f"<span style='color: {RED_COLOR};'>-${delta}</span>"
        st.title(f'{st.session_state.logged_user} corporation system')
        st.markdown(f'## Current balance: ${balance} ({delta_str})', unsafe_allow_html=True)
        stocks_block()
        market_graph()
        expansion_block()


if __name__ == '__main__':
    init_state()
    title = f'{st.session_state.logged_user} corporation dashboard' if st.session_state.logged_user else 'Login'
    st.set_page_config(page_title=title, layout='wide')
    
    sidebar()
    main_panel()
