import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from toolz.functoolz import do


def stocks_block():
    stocks_df = st.session_state.stocks
    with st.beta_expander('Биржевые котировки', expanded=True):
        col1, col2 = st.beta_columns([2, 3])
        with col1:
            st.markdown('<p style="text-align: center;"> Выгрузка с биржи </p>', unsafe_allow_html=True)
            st.dataframe(stocks_df.pivot(index='cycle', columns='ticket', values='price'))
        with col2:
            st.markdown('<p style="text-align: center;"> График котировок акций </p>', unsafe_allow_html=True)
            nearest = alt.selection(type='single', nearest=True, on='mouseover', fields=['cycle'], empty='none')
            x = alt.X('cycle:Q', scale=alt.Scale(domain=(0, st.session_state.cycle)))
            line = alt.Chart(stocks_df).mark_line(point=True).encode(x=x, y='price:Q', color='ticket:N', strokeDash='ticket')
            selectors = alt.Chart(stocks_df).mark_point().encode(x='cycle:Q', opacity=alt.value(0)).add_selection(nearest)
            points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
            text = line.mark_text(align='left', dx=5, dy=-5).encode(text=alt.condition(nearest, 'price:Q', alt.value(' ')))
            rules = alt.Chart(stocks_df).mark_rule(color='gray').encode(x='cycle:Q').transform_filter(nearest)
            layer = alt.layer(line, selectors, points, rules, text).properties(width=800, height=450).interactive()
            st.altair_chart(layer)
