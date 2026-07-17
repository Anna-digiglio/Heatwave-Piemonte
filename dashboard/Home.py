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

from components.constants import MAP_TILES, THEME_COLD, THEME_HOT, THEME_MID, format_mk_trend
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_municipality_geometries_wkt,
    get_overview_stats,
    get_trend_analysis,
)
from components.styling import inject_custom_css, render_hero, render_nav_card_header, render_stats_row
from src.utils.config import config

st.set_page_config(
    page_title=config.get('dashboard.title', 'Heatwave Piemonte'),
    layout='wide',
)
inject_custom_css()

stats = get_overview_stats()
n_years = stats['date_end'].year - stats['date_start'].year + 1

render_hero(
    eyebrow="Analisi spazio-temporale",
    title="Heatwave Piemonte",
    lede=(
        f"<b>{n_years} anni di dati meteorologici reali</b> per capire come sta "
        "cambiando il clima in Piemonte: le temperature stanno davvero salendo? "
        "Ci sono zone della regione più colpite di altre? E quanto sono "
        "diventate più frequenti e intense le <b>ondate di calore</b>?"
    ),
    meta=[
        ("Periodo", f"{stats['date_start'].year}–{stats['date_end'].year}"),
        ("Comuni con dati", f"{stats['n_municipalities_with_data']} / {stats['n_municipalities']}"),
        ("Ultimo aggiornamento", stats['date_end'].strftime('%d/%m/%Y')),
    ],
)

st.subheader("Esplora la dashboard")
CARD_HEIGHT = 280  # altezza fissa: senza, ogni card si dimensiona sul proprio testo (vedi wiki/log.md 2026-07-16)
card1, card2, card3 = st.columns(3)
with card1:
    with st.container(key="navcard-temporale", height=CARD_HEIGHT):
        render_nav_card_header(
            icon="📈", title="Analisi Temporale",
            description=(
                "Le temperature stanno davvero salendo? Trend, anomalie, "
                "confronto tra stagioni e variabilità nel tempo, comune per comune."
            ),
        )
        st.page_link("pages/02_analisi_temporale.py", label="Vai alla pagina →")
with card2:
    with st.container(key="navcard-spaziale", height=CARD_HEIGHT):
        render_nav_card_header(
            icon="🗺️", title="Analisi Spaziale",
            description=(
                "Quali zone del Piemonte sono più calde o si scaldano più in "
                "fretta? Mappe per provincia, fascia altitudinale, isola di "
                "calore urbana."
            ),
        )
        st.page_link("pages/03_analisi_spaziale.py", label="Vai alla pagina →")
with card3:
    with st.container(key="navcard-ondate", height=CARD_HEIGHT):
        render_nav_card_header(
            icon="🔥", title="Ondate di Calore",
            description=(
                "Quando, dove e quanto intense sono state le ondate di calore "
                "dal 2000 a oggi, e se il fenomeno sta accelerando."
            ),
        )
        st.page_link("pages/04_ondate_di_calore.py", label="Vai alla pagina →")

st.divider()

st.warning(
    f"**Limite importante dei dati**: le temperature reali coprono "
    f"**{stats['n_municipalities_with_data']} dei {stats['n_municipalities']} "
    "comuni piemontesi** — gli 8 capoluoghi di provincia più altri comuni "
    "scelti per coprire bene il territorio (zone di montagna, pianura, "
    "collina), non un censimento completo. Ogni grafico e mappa di questo "
    f"sito riflette solo questi {stats['n_municipalities_with_data']} comuni."
)

st.subheader("Il progetto in numeri")
render_stats_row([
    {
        'label': "Righe di temperatura", 'unit': "righe", 'color': THEME_COLD,
        'value': f"{stats['n_temperature_rows']:,}".replace(',', '.'),
        'spark': [0.3, 0.35, 0.5, 0.45, 0.65, 0.6, 0.8, 1.0],
    },
    {
        'label': "Periodo coperto", 'unit': f"{n_years} anni", 'color': THEME_MID,
        'value': f"{stats['date_start'].year}–{stats['date_end'].year}",
        'spark': [0.1, 0.2, 0.3, 0.4, 0.55, 0.7, 0.85, 1.0],
    },
    {
        'label': "Comuni con dati reali", 'unit': f"/ {stats['n_municipalities']}", 'color': THEME_MID,
        'value': str(stats['n_municipalities_with_data']),
        'spark': [0.15, 0.15, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    },
    {
        'label': "Ondate di calore identificate", 'unit': "eventi", 'color': THEME_HOT,
        'value': str(stats['n_heatwaves']),
        'spark': [0.05, 0.1, 0.15, 0.3, 0.4, 0.55, 0.75, 1.0],
    },
])

st.divider()

geo_df = get_municipality_geometries_wkt()
trend_df = get_trend_analysis()

st.subheader("Velocità di riscaldamento per comune")
st.caption(
    f"Ogni comune è colorato in base a quanto si è scaldato tra il "
    f"{stats['date_start'].year} e il {stats['date_end'].year}: più il "
    "colore vira verso il rosso, più il riscaldamento è stato rapido; il "
    "blu segnala le zone rimaste più stabili (o leggermente più fresche). "
    "Passa il mouse su un comune per il valore esatto, oppure scorri la "
    "tabella qui sotto per vedere tutti i numeri insieme."
)
m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)

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

st.subheader(f"Trend di riscaldamento ({stats['date_start'].year}-{stats['date_end'].year})")
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
