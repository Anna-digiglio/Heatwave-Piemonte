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
st.caption("Quando, dove e quanto sono state intense le ondate di calore rilevate dal 2000 a oggi.")

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Un'**ondata di calore** qui è definita come **almeno 3 giorni di fila** "
        "con temperatura massima sopra i **35°C** (vedi anche la Home per il "
        "dettaglio). Per ogni ondata calcoliamo:\n\n"
        "- **Durata**: quanti giorni consecutivi è durata\n"
        "- **Intensità**: quanto la temperatura massima ha superato la soglia "
        "dei 35°C, moltiplicato per la durata — un'ondata lunga e/o molto "
        "calda ha un'intensità più alta di una breve e appena sopra soglia\n\n"
        "Il grafico a barre mostra **quante ondate sono state rilevate ogni anno**, "
        "sommando tutti gli 8 comuni: è un modo rapido per vedere se gli anni "
        "recenti sono peggiori di quelli passati."
    )

freq_df = get_heatwave_frequency_by_year()
if not freq_df.empty:
    fig = px.bar(freq_df, x='year', y='n_heatwaves', labels={'year': 'Anno', 'n_heatwaves': 'N. ondate'})
    fig.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    st.caption(
        "2003 e 2019 emergono come gli anni con più ondate rilevate, coerente con le "
        "note ondate di calore europee di quegli anni. Gli anni recenti (2022-2025) "
        "mostrano più ondate rispetto al primo decennio (2000-2010) — coerente col "
        "trend di riscaldamento visto nella pagina 'Analisi Temporale'."
    )

st.subheader("Statistiche per comune")
st.caption("Quale comune ha avuto più ondate, più lunghe, o più intense?")
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
st.caption("Ogni riga è una singola ondata di calore rilevata: data di inizio/fine, durata e temperature.")
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
