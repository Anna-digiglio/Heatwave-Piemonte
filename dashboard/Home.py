"""
Home.py - Heatwave Piemonte Dashboard (pagina principale)

Entry point Streamlit. Le altre pagine sono in `pages/` (convenzione
multipage di Streamlit): 02_analisi_temporale, 03_analisi_spaziale,
04_ondate_di_calore, 05_download_dati.

Usage:
    streamlit run dashboard/Home.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import folium
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

from components.constants import format_mk_trend
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_municipality_geometries_wkt,
    get_overview_stats,
    get_trend_analysis,
)
from components.styling import inject_custom_css
from src.utils.config import config

st.set_page_config(
    page_title=config.get('dashboard.title', 'Heatwave Piemonte'),
    layout='wide',
)
inject_custom_css()

st.title("🌡️ Heatwave Piemonte")
st.caption("Analisi spazio-temporale delle ondate di calore in Piemonte (2000-2025)")

st.markdown(
     "Questo progetto analizza **26 anni di dati meteorologici reali** per "
    "capire come sta cambiando il clima in Piemonte: le temperature stanno "
    "davvero salendo? Ci sono zone della regione più colpite di altre? E "
    "quanto sono diventate più frequenti e intense le **ondate di calore**?"
)

st.subheader("Esplora la dashboard")
card1, card2, card3 = st.columns(3)
with card1:
    with st.container(border=True):
        st.markdown("### 📈 Analisi Temporale")
        st.caption(
            "Le temperature stanno davvero salendo? Trend, anomalie, "
            "confronto tra stagioni e variabilità nel tempo, comune per comune."
        )
        st.page_link("pages/02_analisi_temporale.py", label="Vai alla pagina →")
with card2:
    with st.container(border=True):
        st.markdown("### 🗺️ Analisi Spaziale")
        st.caption(
            "Quali zone del Piemonte sono più calde o si scaldano più in "
            "fretta? Mappe per provincia, fascia altitudinale, isola di "
            "calore urbana."
        )
        st.page_link("pages/03_analisi_spaziale.py", label="Vai alla pagina →")
with card3:
    with st.container(border=True):
        st.markdown("### 🔥 Ondate di Calore")
        st.caption(
            "Quando, dove e quanto intense sono state le ondate di calore "
            "dal 2000 a oggi, e se il fenomeno sta accelerando."
        )
        st.page_link("pages/04_ondate_di_calore.py", label="Vai alla pagina →")

st.divider()

with st.expander("ℹ️ Cos'è un'ondata di calore?"):
    st.markdown(
        "Definiamo **ondata di calore** una sequenza di **almeno 3 giorni "
        "consecutivi** in cui la temperatura massima supera i **35°C**. "
        "È una definizione semplificata (i climatologi spesso usano soglie "
        "che variano località per località, non un numero fisso), scelta "
        "qui per essere facile da capire e da verificare. Il calcolo è "
        "fatto da una funzione che "
        "scandisce anno per anno le temperature di ogni comune."
    )

st.warning(
    "**Limite importante dei dati**: le temperature reali coprono **44 dei "
    "1180 comuni piemontesi** — gli 8 capoluoghi di provincia più 36 comuni "
    "scelti per coprire bene il territorio (zone di montagna, pianura, "
    "collina), non un censimento completo. Ogni grafico e mappa di questo "
    "sito riflette solo questi 44 comuni. "
)

stats = get_overview_stats()

st.subheader("Il progetto in numeri")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Righe di temperatura", f"{stats['n_temperature_rows']:,}".replace(',', '.'))
col1.caption("Una misura al giorno, per comune, dal 2000 a oggi")
col2.metric(
    "Periodo coperto",
    f"{stats['date_start'].year}–{stats['date_end'].year}",
)
col2.caption("26 anni di storia climatica")
col3.metric("Comuni con dati reali", f"{stats['n_municipalities_with_data']} / {stats['n_municipalities']}")
col3.caption("8 capoluoghi + 36 comuni scelti per coprire il territorio")
col4.metric("Ondate di calore identificate", stats['n_heatwaves'])
col4.caption("Sequenze di 3+ giorni sopra i 35°C")

st.divider()

geo_df = get_municipality_geometries_wkt()
trend_df = get_trend_analysis()

col_map, col_trend = st.columns([3, 2])

with col_map:
    st.subheader("Velocità di riscaldamento per comune")
    st.caption(
        "Colore = pendenza del trend 2000-2025 (°C/decade): rosso = si scalda "
        "più in fretta, blu = più lentamente (o si raffredda). Passa il mouse "
        "per il valore esatto — dettaglio nella tabella qui a fianco."
    )
    m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')

    if trend_df.empty:
        for _, row in geo_df.iterrows():
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']} ({row['province_name']})",
                style_function=lambda _: {'fillColor': '#e74c3c', 'color': '#c0392b', 'fillOpacity': 0.5},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[])
        st.info("Esegui `python -m src.analysis.trend_analysis` per colorare la mappa per trend.")
    else:
        merged = geo_df.merge(trend_df[['municipality_name', 'lr_slope_per_decade']], on='municipality_name')
        max_abs_slope = merged['lr_slope_per_decade'].abs().max() or 1
        cmap_trend = LinearColormap(['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_slope, vmax=max_abs_slope)

        for _, row in merged.iterrows():
            color = cmap_trend(row['lr_slope_per_decade'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']}: {row['lr_slope_per_decade']:+.2f} °C/decade",
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.75},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[])
        render_gradient_legend(
            cmap_trend, -max_abs_slope, max_abs_slope,
            labels=["Raffreddamento", "Riscaldamento lento", "Riscaldamento moderato",
                    "Riscaldamento sostenuto", "Riscaldamento rapido"],
            unit="°C/decade", title="Legenda — velocità di riscaldamento", signed=True,
        )

with col_trend:
    st.subheader("Trend di riscaldamento (2000-2025)")
    st.caption("La temperatura media di ogni comune sta salendo, scendendo, o restando stabile?")
    if trend_df.empty:
        st.info("Esegui `python -m src.analysis.trend_analysis` per generare questi risultati.")
    else:
        display_df = trend_df[['municipality_name', 'mk_trend', 'lr_slope_per_decade', 'lr_p_value']].copy()
        display_df['mk_trend'] = display_df['mk_trend'].apply(format_mk_trend)
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
