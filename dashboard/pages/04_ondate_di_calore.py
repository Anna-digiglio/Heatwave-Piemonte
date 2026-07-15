"""
04_ondate_di_calore.py - Statistiche ed elenco delle ondate di calore.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import streamlit as st

from components.queries import (
    get_heatwave_events,
    get_heatwave_frequency_by_year,
    get_heatwave_stats_by_municipality,
)

st.set_page_config(page_title='Ondate di Calore — Heatwave Piemonte', layout='wide')
st.title("🔥 Ondate di Calore")
st.caption("Sequenze di ≥3 giorni consecutivi con temp_max > 35°C (identify_heatwaves())")

freq_df = get_heatwave_frequency_by_year()
if not freq_df.empty:
    fig = px.bar(freq_df, x='year', y='n_heatwaves', labels={'year': 'Anno', 'n_heatwaves': 'N. ondate'})
    fig.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    st.caption(
        "2003 e 2019 emergono come gli anni con più ondate rilevate, coerente con le "
        "note ondate di calore europee di quegli anni."
    )

st.subheader("Statistiche per comune")
by_muni = get_heatwave_stats_by_municipality()
if by_muni.empty:
    st.info("Esegui `python -m src.analysis.heatwave_stats` per generare questi risultati.")
else:
    st.dataframe(
        by_muni.rename(columns={
            'municipality_name': 'Comune', 'n_heatwaves': 'N. ondate',
            'avg_duration_days': 'Durata media (gg)', 'max_duration_days': 'Durata max (gg)',
            'avg_intensity': 'Intensità media', 'max_intensity': 'Intensità max',
            'avg_max_temp': 'Temp. max media (°C)',
        }),
        hide_index=True, width='stretch',
    )

st.subheader("Elenco ondate")
events = get_heatwave_events()
municipality_filter = st.multiselect("Filtra per comune", sorted(events['municipality_name'].unique()))
if municipality_filter:
    events = events[events['municipality_name'].isin(municipality_filter)]

st.dataframe(
    events.rename(columns={
        'municipality_name': 'Comune', 'province_name': 'Provincia',
        'start_date': 'Inizio', 'end_date': 'Fine', 'duration_days': 'Durata (gg)',
        'max_temp': 'Temp. max (°C)', 'mean_temp': 'Temp. media (°C)', 'intensity_index': 'Intensità',
    }),
    hide_index=True, width='stretch',
)
