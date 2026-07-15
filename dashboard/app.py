"""
app.py - Heatwave Piemonte Dashboard (Home)

Entry point Streamlit. Le altre pagine sono in `pages/` (convenzione
multipage di Streamlit): 02_analisi_temporale, 03_analisi_spaziale,
04_ondate_di_calore, 05_download_dati.

Usage:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import folium
import streamlit as st
from streamlit_folium import st_folium

from components.maps import wkt_to_geojson
from components.queries import (
    get_municipality_geometries_wkt,
    get_overview_stats,
    get_trend_analysis,
)
from src.utils.config import config

st.set_page_config(
    page_title=config.get('dashboard.title', 'Heatwave Piemonte'),
    layout='wide',
)

st.title("🌡️ Heatwave Piemonte")
st.caption("Analisi spazio-temporale delle ondate di calore in Piemonte (2000-2025)")

st.warning(
    "I dati di temperatura reali coprono solo gli **8 comuni capoluogo di "
    "provincia** (unica granularità scaricata da Open-Meteo), non tutti i "
    "1180 comuni piemontesi. Vedi la wiki (`etl-pipeline.md`) per il dettaglio."
)

stats = get_overview_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Righe di temperatura", f"{stats['n_temperature_rows']:,}".replace(',', '.'))
col2.metric(
    "Periodo coperto",
    f"{stats['date_start'].year}–{stats['date_end'].year}",
)
col3.metric("Comuni con dati reali", f"{stats['n_municipalities_with_data']} / {stats['n_municipalities']}")
col4.metric("Ondate di calore identificate", stats['n_heatwaves'])

st.divider()

col_map, col_trend = st.columns([3, 2])

with col_map:
    st.subheader("Comuni con dati di temperatura reali")
    geo_df = get_municipality_geometries_wkt()

    m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
    for _, row in geo_df.iterrows():
        folium.GeoJson(
            wkt_to_geojson(row['geometry_wkt']),
            name=row['municipality_name'],
            tooltip=f"{row['municipality_name']} ({row['province_name']})",
            style_function=lambda _: {'fillColor': '#e74c3c', 'color': '#c0392b', 'fillOpacity': 0.5},
        ).add_to(m)
    st_folium(m, width=None, height=420, returned_objects=[])

with col_trend:
    st.subheader("Trend di riscaldamento (2000-2025)")
    trend_df = get_trend_analysis()
    if trend_df.empty:
        st.info("Esegui `python -m src.analysis.trend_analysis` per generare questi risultati.")
    else:
        display_df = trend_df[['municipality_name', 'mk_trend', 'lr_slope_per_decade', 'lr_p_value']].copy()
        display_df.columns = ['Comune', 'Trend (Mann-Kendall)', '°C/decade', 'p-value']
        display_df['°C/decade'] = display_df['°C/decade'].round(2)
        display_df['p-value'] = display_df['p-value'].round(4)
        st.dataframe(display_df, hide_index=True, width='stretch')
        st.caption("Trend significativo se p-value < 0.05. Vedi pagina 'Analisi Temporale' per il dettaglio.")

st.divider()
st.caption(
    "Progetto portfolio Data Engineering/GIS — vedi la wiki del repository "
    "(`wiki/index.md`) per lo stato dettagliato pianificato-vs-implementato."
)
