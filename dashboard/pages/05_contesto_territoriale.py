"""
05_contesto_territoriale.py - Uso del suolo, densità di popolazione e NDVI per
tutti i 1180 comuni piemontesi, e il loro legame con la temperatura osservata.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import numpy as np
import plotly.express as px
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

from components.charts import apply_chart_theme
from components.constants import (
    LAND_COVER_COLORS, LAND_COVER_LABELS, MAP_TILES, NDVI_COLORS,
    VEGETATION_CLASS_LABELS, elevation_band,
)
from components.filters import render_province_filter, render_year_range_filter
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_all_municipality_geometries_wkt,
    get_kpi_annual,
    get_land_cover_all,
    get_land_cover_with_population,
    get_municipality_metadata,
    get_ndvi_all,
)
from components.styling import inject_custom_css

st.set_page_config(page_title='Contesto Territoriale — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("🌍 Contesto Territoriale")
st.caption(
    "Uso del suolo, densità di popolazione e verde da satellite per tutti i 1180 comuni "
    "piemontesi — non solo quelli con dati di temperatura — e come si legano al clima "
    "osservato in Analisi Spaziale."
)

provinces = render_province_filter(key='territoriale_province')
st.caption(
    "Il filtro sopra si applica a tutte le mappe di questa pagina. Uso del suolo, "
    "popolazione e NDVI sono uno scatto recente, non una serie temporale, quindi qui non "
    "serve un filtro anni — tranne che per il grafico finale, che confronta questi dati "
    "con la temperatura e ha il proprio selettore di periodo."
)

metadata = get_municipality_metadata()
metadata_f = metadata[metadata['province_name'].isin(provinces)]
geo_all = get_all_municipality_geometries_wkt()

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "- Le mappe di **uso del suolo**, **densità di popolazione** e **NDVI** (CORINE Land "
        "Cover 2018, ISTAT, Copernicus Global Land Service) coprono tutti i 1180 comuni "
        "piemontesi, non solo quelli con temperatura — servono a esplorare *perché* certe "
        "zone potrebbero risultare più calde, non solo *dove* lo sono.\n"
        "- Per le mappe di temperatura, trend, cluster climatici e indice di Moran vedi la "
        "pagina Analisi Spaziale (link sotto).\n"
        "- Il grafico finale incrocia questi dati con la temperatura osservata: guarda anche "
        "la fascia altitudinale del comune, perché la quota resta il fattore che pesa di più."
    )
st.page_link("pages/03_analisi_spaziale.py", label="← Torna ad Analisi Spaziale (mappe di temperatura, trend, cluster)")

st.subheader("Uso del suolo per comune")
st.caption(
    "Classe di uso del suolo dominante (CORINE Land Cover 2018, "
    "Copernicus) per ciascuno dei 1180 comuni piemontesi — non solo "
    "quelli con dati di temperatura. \"Urbano/artificiale\" include "
    "residenziale, industriale, trasporti e verde urbano; il dettaglio "
    "per sotto-classe è nel grafico più sotto."
)
land_cover_all = get_land_cover_all()
lc_geo = geo_all.merge(land_cover_all.drop(columns=['province_name']), on='municipality_name')
lc_geo_f = lc_geo[lc_geo['province_name'].isin(provinces)]

if lc_geo_f.empty:
    st.info("Nessun comune per il filtro provincia scelto.")
else:
    m_lc = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
    for _, row in lc_geo_f.iterrows():
        color = LAND_COVER_COLORS.get(row['dominant_class'], '#cccccc')
        folium.GeoJson(
            wkt_to_geojson(row['geometry_wkt']),
            tooltip=f"{row['municipality_name']}: {LAND_COVER_LABELS.get(row['dominant_class'], row['dominant_class'])}",
            style_function=lambda _, c=color: {'fillColor': c, 'color': '#999', 'weight': 0.3, 'fillOpacity': 0.8},
        ).add_to(m_lc)
    st_folium(m_lc, width=None, height=420, returned_objects=[], key='map_land_cover')
    legend_rows = ''.join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">'
        f'<span style="display:inline-block;width:22px;height:14px;background:{LAND_COVER_COLORS[k]};'
        f'border:1px solid rgba(0,0,0,0.3);border-radius:3px;flex-shrink:0;"></span>'
        f'<span style="font-size:0.85rem;">{v}</span></div>'
        for k, v in LAND_COVER_LABELS.items()
    )
    st.markdown(f'<div style="margin:0.25rem 0 0.75rem 0;">{legend_rows}</div>', unsafe_allow_html=True)

st.subheader("Densità di popolazione")
st.caption(
    "Popolazione residente (stima ISTAT 1° gennaio 2026) diviso "
    "superficie comunale — tutti i 1180 comuni. Scala logaritmica: senza, "
    "Torino schiaccerebbe la scala rendendo illeggibili tutte le "
    "differenze tra gli altri comuni."
)
pop_geo = geo_all.merge(land_cover_all[['municipality_name', 'population', 'area_km2', 'pop_density']],
                         on='municipality_name')
pop_geo_f = pop_geo[pop_geo['province_name'].isin(provinces) & pop_geo['pop_density'].notna()]

if pop_geo_f.empty:
    st.info("Nessun dato di popolazione per il filtro scelto.")
else:
    log_density = np.log10(pop_geo_f['pop_density'].clip(lower=0.1))
    cmap_pop = LinearColormap(['#fef0d9', '#fc8d59', '#b30000'], vmin=log_density.min(), vmax=log_density.max())
    m_pop = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
    for (_, row), log_val in zip(pop_geo_f.iterrows(), log_density):
        color = cmap_pop(log_val)
        folium.GeoJson(
            wkt_to_geojson(row['geometry_wkt']),
            tooltip=f"{row['municipality_name']}: {row['pop_density']:.0f} ab/km² ({row['population']:.0f} ab.)",
            style_function=lambda _, c=color: {'fillColor': c, 'color': '#999', 'weight': 0.3, 'fillOpacity': 0.8},
        ).add_to(m_pop)
    st_folium(m_pop, width=None, height=420, returned_objects=[], key='map_population')
    st.caption(
        f"Da {10**log_density.min():.1f} a {10**log_density.max():.0f} ab/km² "
        "nel filtro attuale (scala log)."
    )

st.subheader("NDVI — verde da satellite")
st.caption(
    "Indice di vegetazione (NDVI, Copernicus Global Land Service, "
    "composito 10-giornaliero inizio luglio 2026) per tutti i 1180 "
    "comuni — misura **continua** di quanto verde c'è, complementare "
    "alla classe di uso del suolo dominante sopra: due comuni "
    "entrambi \"urbani\" per CORINE possono avere quantità di verde "
    "molto diverse (es. per via di parchi/alberature)."
)
ndvi_all = get_ndvi_all()
ndvi_geo = geo_all.merge(ndvi_all.drop(columns=['province_name']), on='municipality_name')
ndvi_geo_f = ndvi_geo[ndvi_geo['province_name'].isin(provinces)]

if ndvi_geo_f.empty:
    st.info("Nessun dato NDVI per il filtro scelto.")
else:
    ndvi_min, ndvi_max = ndvi_geo_f['ndvi_mean'].min(), ndvi_geo_f['ndvi_mean'].max()
    cmap_ndvi = LinearColormap(NDVI_COLORS, vmin=ndvi_min, vmax=ndvi_max)
    m_ndvi = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
    for _, row in ndvi_geo_f.iterrows():
        color = cmap_ndvi(row['ndvi_mean'])
        veg_label = VEGETATION_CLASS_LABELS.get(row['vegetation_class'], row['vegetation_class'])
        folium.GeoJson(
            wkt_to_geojson(row['geometry_wkt']),
            tooltip=f"{row['municipality_name']}: NDVI {row['ndvi_mean']:.2f} ({veg_label})",
            style_function=lambda _, c=color: {'fillColor': c, 'color': '#999', 'weight': 0.3, 'fillOpacity': 0.8},
        ).add_to(m_ndvi)
    st_folium(m_ndvi, width=None, height=420, returned_objects=[], key='map_ndvi')
    render_gradient_legend(
        cmap_ndvi, ndvi_min, ndvi_max,
        labels=["Rado", "Scarso", "Moderato", "Denso", "Molto denso"],
        unit="NDVI", title="Legenda — NDVI (verde da satellite)", decimals=2,
    )

st.subheader("Temperatura, uso del suolo e popolazione")
year_start, year_end = render_year_range_filter(key='territoriale_year_range')
st.caption(
    "Ogni punto è un comune **con dati di temperatura reali** "
    f"({metadata_f.shape[0]} nel filtro attuale, periodo {year_start}-{year_end}, "
    "sempre su Open-Meteo — è la fonte a cui è legato il modello di regressione spaziale "
    "citato sotto). Colore = fascia "
    "altitudinale (la quota è il fattore che pesa di più, vedi Analisi Spaziale); "
    "posizione orizzontale = quanto suolo urbano/industriale ha "
    "il comune. Se, **a parità di colore** (cioè a parità di quota), i "
    "punti più a destra tendono a stare più in alto, è un indizio "
    "(non una prova) che l'urbanizzazione conta anche al netto "
    "dell'altitudine."
)
annual = get_kpi_annual()
annual_f = annual[(annual['year'] >= year_start) & (annual['year'] <= year_end)]
lc_pop = get_land_cover_with_population()
annual_avg = annual_f.groupby('municipality_name')['temp_mean_annual'].mean().reset_index()
scatter_df = annual_avg.merge(lc_pop, on='municipality_name').merge(
    metadata_f[['municipality_name', 'elevation_m']], on='municipality_name'
).merge(ndvi_all[['municipality_name', 'ndvi_mean']], on='municipality_name', how='left')
scatter_df = scatter_df[scatter_df['province_name'].isin(provinces)]

x_variable = st.radio(
    "Variabile in ascissa", ['pct_urban', 'pct_industrial_commercial', 'pop_density', 'ndvi_mean'],
    format_func=lambda v: {'pct_urban': '% suolo urbano/artificiale',
                            'pct_industrial_commercial': '% industriale/commerciale',
                            'pop_density': 'Densità di popolazione (ab/km²)',
                            'ndvi_mean': 'NDVI medio (verde da satellite)'}[v],
    horizontal=True, key='uhi_x_variable',
)

if scatter_df.empty:
    st.info("Dati insufficienti per il filtro scelto.")
else:
    scatter_df = scatter_df.copy()
    scatter_df['fascia'] = scatter_df['elevation_m'].apply(elevation_band)
    fig_scatter = px.scatter(
        scatter_df, x=x_variable, y='temp_mean_annual', color='fascia',
        category_orders={'fascia': ['Pianura', 'Collina', 'Montagna']},
        color_discrete_map={'Pianura': '#e74c3c', 'Collina': '#f39c12', 'Montagna': '#3498db'},
        hover_name='municipality_name',
        labels={
            'pct_urban': '% suolo urbano/artificiale',
            'pct_industrial_commercial': '% industriale/commerciale',
            'pop_density': 'Densità di popolazione (ab/km²)',
            'ndvi_mean': 'NDVI medio',
            'temp_mean_annual': 'Temp. media annuale (°C)', 'fascia': 'Fascia altitudinale',
        },
    )
    if x_variable == 'pop_density':
        fig_scatter.update_xaxes(type='log')
    fig_scatter.update_layout(height=380, margin=dict(t=10, b=10), legend=dict(orientation='h'))
    st.plotly_chart(apply_chart_theme(fig_scatter), width='stretch')

    corr = scatter_df[x_variable].corr(scatter_df['temp_mean_annual'])
    st.metric("Correlazione (Pearson r, tutti i comuni nel filtro)", f"{corr:+.2f}")
    st.caption(
        "Correlazione semplice, **non controllata per quota** (a differenza "
        "della lettura \"a parità di colore\" suggerita sopra) — un valore "
        "alto qui può derivare in parte dal fatto che i comuni di pianura "
        "sono sia più caldi sia più urbanizzati. Un modello che isola "
        "l'effetto di ciascuna variabile dalle altre (regressione a errore "
        "spaziale) esiste già: controllando per elevazione, con il "
        "campione esteso a 234 comuni (2026-07-19) **% urbano è diventato "
        "significativo** (p=0.031, coefficiente +0.0083 — prima p=0.19, "
        "non significativo), mentre **NDVI resta non significativo e il "
        "suo coefficiente continua a restringersi verso zero** (+0.10, "
        "p=0.66 — era +0.16 col campione precedente, +1.09 con quello "
        "ancora prima) — solo l'elevazione resta un predittore robusto in "
        "ogni versione del modello. Il cambio di significatività di % "
        "urbano tra un aggiornamento e l'altro (non solo di grandezza) è "
        "un segnale che il modello non si è ancora stabilizzato: da "
        "verificare se regge anche alla prossima estensione del campione "
        "prima di trattarlo come un risultato solido, non solo un "
        "artefatto di soglia p=0.05. Risultato ancora provvisorio "
        "(n=234 comuni)."
    )

st.subheader("Metodologia")
st.markdown(
    "Alcune scelte fatte in questa pagina, spiegate:\n\n"
    "- **Perché lo scatter uso del suolo/temperatura non è un vero "
    "studio dell'effetto isola di calore?** Mostra una correlazione tra "
    "tutti i comuni con dati, colorata per fascia altitudinale così da "
    "poter almeno *guardare a occhio* se l'effetto regge a parità di "
    "quota — ma il coefficiente di correlazione mostrato resta "
    "calcolato su tutti i comuni insieme, senza isolare "
    "matematicamente l'effetto della quota da quello dell'uso del "
    "suolo. Un modello che lo fa **esiste**: una regressione OLS con "
    "elevazione+popolazione+%urbano+NDVI, seguita da un modello a "
    "errore spaziale dato che l'indice di Moran sui residui restava "
    "significativo (vedi Analisi Spaziale). Risultato: "
    "l'effetto urbano diventa significativo col segno atteso solo nel "
    "modello spaziale — l'OLS classico lo mascherava. Risultato "
    "provvisorio, da confermare al crescere del campione di comuni.\n"
    "- **Da dove viene l'uso del suolo, e che limite ha?** CORINE Land "
    "Cover 2018 (Copernicus) — uno scatto del 2018, confrontato qui "
    "con le temperature dell'intero periodo disponibile e popolazione "
    "stimata 2026. L'uso del "
    "suolo cambia lentamente (un'epoca CORINE copre ~6 anni), quindi è "
    "un compromesso accettabile, ma non un dato perfettamente "
    "allineato nel tempo con gli altri due.\n"
    "- **Da dove viene l'NDVI, e che limite ha?** Copernicus Global "
    "Land Service NDVI 300m V3 — un **singolo composito di 10 giorni** "
    "(inizio luglio 2026), non una media pluriennale come le "
    "temperature: cattura la vegetazione di quel periodo specifico "
    "(piena stagione vegetativa), non un valore \"tipico\" stabile nel "
    "tempo. Un composito invernale darebbe una mappa molto diversa."
)
