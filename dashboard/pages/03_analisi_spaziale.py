"""
03_analisi_spaziale.py - Mappe coropletiche, trend per zona, fasce
altitudinali, isola di calore urbana, cluster climatici e Moran's I.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

from components.charts import apply_chart_theme
from components.constants import (
    CLUSTER_COLORS, LAND_COVER_COLORS, LAND_COVER_LABELS, MAP_TILES,
    NDVI_COLORS, TEMPERATURE_COLORSCALE, TREND_COLORSCALE, VEGETATION_CLASS_LABELS,
    elevation_band,
)
from components.filters import render_province_filter, render_year_range_filter
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_all_municipality_geometries_wkt,
    get_kpi_annual,
    get_kpi_annual_by_province,
    get_land_cover_all,
    get_land_cover_with_population,
    get_morans_i_summary,
    get_municipality_geometries_wkt,
    get_municipality_metadata,
    get_ndvi_all,
    get_province_geometries_wkt,
    get_spatial_analysis,
    get_trend_analysis,
)
from components.styling import inject_custom_css

st.set_page_config(page_title='Analisi Spaziale — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("🗺️ Analisi Spaziale")
st.caption("Ci sono zone del Piemonte più calde di altre? Il riscaldamento è uguale ovunque? La quota conta?")

col_year, col_prov = st.columns(2)
with col_year:
    year_start, year_end = render_year_range_filter(key='spaziale_year_range')
with col_prov:
    provinces = render_province_filter(key='spaziale_province')
st.caption("Entrambi i filtri sopra si applicano a tutte le mappe e i grafici di questa pagina.")

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "- La **mappa coropletica** colora ogni provincia in base alla "
        "temperatura media nel periodo selezionato (blu = più fresco, "
        "rosso = più caldo) — confine reale ottenuto unendo via PostGIS "
        "(`ST_Union`) le geometrie di tutti i comuni della provincia.\n"
        "- La **mappa del trend** usa invece una scala **divergente** "
        "centrata sullo zero: rosso = si scalda più velocemente, blu = più "
        "lentamente (o si raffredda). Non va confusa con la mappa sopra — "
        "qui il colore rappresenta una *velocità di cambiamento*, non una "
        "temperatura assoluta.\n"
        "- **Cluster climatici** (tab Dettaglio) raggruppano i comuni simili "
        "con K-means; l'**indice di Moran** misura se i comuni vicini hanno "
        "anche temperature simili.\n"
        "- Le mappe di **uso del suolo**, **densità di popolazione** e "
        "**NDVI** (CORINE Land Cover 2018, ISTAT, Copernicus Global Land "
        "Service) coprono tutti i 1180 comuni piemontesi, non solo quelli "
        "con temperatura — servono a esplorare *perché* certe zone "
        "potrebbero risultare più calde, non solo *dove* lo sono."
    )

metadata = get_municipality_metadata()

st.info(
    f"{len(metadata)} comuni con dati reali su 1180 totali (8 capoluoghi + "
    f"{len(metadata) - 8} scelti per coprire il territorio). Le mappe "
    "provinciali aggregano solo i comuni disponibili in ciascuna provincia "
    "— vedi `wiki/pages/etl-pipeline.md`."
)
metadata_f = metadata[metadata['province_name'].isin(provinces)]

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

# --- Dati aggregati per provincia, filtrati per periodo -------------------
kpi_province = get_kpi_annual_by_province()
kpi_province_f = kpi_province[
    (kpi_province['year'] >= year_start) & (kpi_province['year'] <= year_end)
    & (kpi_province['province_name'].isin(provinces))
]
province_avg = kpi_province_f.groupby('province_name').agg(
    temp_mean_annual=('temp_mean_annual', 'mean'),
    days_gt_30c=('days_gt_30c', 'mean'),
).reset_index()

trend_df = get_trend_analysis()
trend_with_province = trend_df.merge(metadata[['municipality_name', 'province_name']], on='municipality_name')
province_trend = trend_with_province[trend_with_province['province_name'].isin(provinces)].groupby(
    'province_name'
)['lr_slope_per_decade'].mean().reset_index()

if not province_avg.empty:
    top_hot = province_avg.loc[province_avg['temp_mean_annual'].idxmax()]
    top_trend_row = province_trend.loc[province_trend['lr_slope_per_decade'].idxmax()] if not province_trend.empty else None
else:
    top_hot, top_trend_row = None, None

top_elev = metadata_f.loc[metadata_f['elevation_m'].idxmax()] if not metadata_f.empty and metadata_f['elevation_m'].notna().any() else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Provincia più calda", top_hot['province_name'] if top_hot is not None else "n/d",
          f"{top_hot['temp_mean_annual']:.1f} °C" if top_hot is not None else None)
k1.caption(f"Media {year_start}-{year_end}")
k2.metric("Provincia con trend più rapido", top_trend_row['province_name'] if top_trend_row is not None else "n/d",
          f"{top_trend_row['lr_slope_per_decade']:+.2f} °C/decade" if top_trend_row is not None else None)
k2.caption("Media dei comuni con dati nella provincia, intero periodo disponibile")
k3.metric("Comune più in quota", top_elev['municipality_name'] if top_elev is not None else "n/d",
          f"{top_elev['elevation_m']:.0f} m" if top_elev is not None else None)
k3.caption("Tra i comuni filtrati")
k4.metric("Comuni con dati (filtro attuale)", len(metadata_f))
k4.caption(f"Su {len(metadata)} comuni totali con dati reali")

with tab_overview:
    st.subheader("Temperatura media per provincia")
    st.caption(
        "Passa il mouse su una provincia per il valore esatto. Colore = "
        "temperatura media nel periodo selezionato nella sidebar."
    )
    province_geo = get_province_geometries_wkt()
    merged_province = province_geo.merge(province_avg, on='province_name', how='left')

    if merged_province['temp_mean_annual'].notna().any():
        vmin, vmax = merged_province['temp_mean_annual'].min(), merged_province['temp_mean_annual'].max()
        cmap_temp = LinearColormap(['#3498db', '#f7f7f7', '#e74c3c'], vmin=vmin, vmax=vmax)

        m1 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
        for _, row in merged_province.iterrows():
            if pd.isna(row['temp_mean_annual']):
                color = '#cccccc'
                tooltip = f"{row['province_name']}: nessun dato nel periodo/filtro scelto"
            else:
                color = cmap_temp(row['temp_mean_annual'])
                tooltip = f"{row['province_name']}: {row['temp_mean_annual']:.1f} °C"
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=tooltip,
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.75},
            ).add_to(m1)
        st_folium(m1, width=None, height=420, returned_objects=[], key='map_temp_province')
        render_gradient_legend(
            cmap_temp, vmin, vmax,
            labels=["Più fresco", "Fresco", "Nella media", "Caldo", "Più caldo"],
            unit="°C", title="Legenda — temperatura media",
        )
    else:
        st.info("Nessun dato di temperatura per le province/periodo selezionati.")

    st.subheader("Velocità di riscaldamento per comune")
    st.caption(
        "Ogni comune è colorato per **pendenza del trend** (°C/decade, intero "
        "periodo disponibile, non ricalcolato sul filtro anni — richiede la "
        "serie giornaliera completa). Rosso = si scalda più in fretta della "
        "media, blu = più lentamente. Il colore è centrato sullo zero: due "
        "sfumature di rosso diverse indicano comunque due velocità diverse "
        "di riscaldamento, non caldo/freddo assoluto."
    )
    geo_df = get_municipality_geometries_wkt()
    trend_points = trend_df.merge(geo_df, on='municipality_name')
    trend_points_f = trend_points[trend_points['province_name'].isin(provinces)]

    if trend_points_f.empty:
        st.info("Nessun comune con trend disponibile per il filtro scelto.")
    else:
        max_abs_slope = trend_points_f['lr_slope_per_decade'].abs().max() or 1
        cmap_trend = LinearColormap(
            ['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_slope, vmax=max_abs_slope
        )
        m2 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
        for _, row in trend_points_f.iterrows():
            color = cmap_trend(row['lr_slope_per_decade'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']}: {row['lr_slope_per_decade']:+.2f} °C/decade",
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 0.5, 'fillOpacity': 0.85},
            ).add_to(m2)
        st_folium(m2, width=None, height=420, returned_objects=[], key='map_trend_points')
        render_gradient_legend(
            cmap_trend, -max_abs_slope, max_abs_slope,
            labels=["Raffreddamento", "Riscaldamento lento", "Riscaldamento moderato",
                    "Riscaldamento sostenuto", "Riscaldamento rapido"],
            unit="°C/decade", title="Legenda — velocità di riscaldamento", signed=True,
        )

    st.subheader("Temperatura per fascia altitudinale")
    st.caption(
        "I comuni sono divisi in 3 fasce in base all'elevazione del loro "
        "centroide: **Pianura** (<300 m), **Collina** (300-700 m), "
        "**Montagna** (>700 m). Il grafico mostra quanto la quota fa "
        "davvero la differenza sulla temperatura media."
    )
    annual = get_kpi_annual()
    annual_f = annual[(annual['year'] >= year_start) & (annual['year'] <= year_end)]
    annual_elev = annual_f.merge(metadata_f[['municipality_name', 'elevation_m']], on='municipality_name')

    if annual_elev.empty:
        st.info("Nessun dato di elevazione disponibile per il filtro scelto.")
    else:
        annual_elev['fascia'] = annual_elev['elevation_m'].apply(elevation_band)
        fig_elev = px.box(
            annual_elev, x='fascia', y='temp_mean_annual',
            category_orders={'fascia': ['Pianura', 'Collina', 'Montagna']},
            color='fascia',
            color_discrete_map={'Pianura': '#e74c3c', 'Collina': '#f39c12', 'Montagna': '#3498db'},
            labels={'fascia': 'Fascia altitudinale', 'temp_mean_annual': 'Temp. media annuale (°C)'},
        )
        fig_elev.update_layout(height=350, margin=dict(t=10, b=10), showlegend=False)
        st.plotly_chart(apply_chart_theme(fig_elev), width='stretch')

    st.subheader("Uso del suolo per comune")
    st.caption(
        "Classe di uso del suolo dominante (CORINE Land Cover 2018, "
        "Copernicus) per ciascuno dei 1180 comuni piemontesi — non solo "
        "quelli con dati di temperatura. \"Urbano/artificiale\" include "
        "residenziale, industriale, trasporti e verde urbano; il dettaglio "
        "per sotto-classe è nel grafico più sotto."
    )
    land_cover_all = get_land_cover_all()
    geo_all = get_all_municipality_geometries_wkt()
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
    st.caption(
        "Ogni punto è un comune **con dati di temperatura reali** "
        f"({metadata_f.shape[0]} nel filtro attuale). Colore = fascia "
        "altitudinale (la quota è il fattore che pesa di più, vedi grafico "
        "sopra); posizione orizzontale = quanto suolo urbano/industriale ha "
        "il comune. Se, **a parità di colore** (cioè a parità di quota), i "
        "punti più a destra tendono a stare più in alto, è un indizio "
        "(non una prova) che l'urbanizzazione conta anche al netto "
        "dell'altitudine."
    )
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
            "l'effetto di ciascuna variabile dalle altre esiste già "
            "(`src/analysis/spatial_regression.py`, modello a errore "
            "spaziale): controllando per elevazione, **% urbano risulta "
            "davvero significativo** (segno atteso: più urbano → più "
            "caldo), mentre l'NDVI resta significativo ma con segno "
            "controintuitivo (più verde → più caldo, probabile "
            "confondimento con l'agricoltura di pianura) — vedi "
            "`wiki/pages/statistical-analysis.md` per il dettaglio "
            "completo, risultato ancora provvisorio (n=63 comuni)."
        )

with tab_detail:
    spatial_df = get_spatial_analysis()
    geo_df = get_municipality_geometries_wkt()

    st.subheader("Cluster climatici (K-means, k=3)")
    st.markdown(
        "**Cos'è un \"cluster\" e come viene deciso?** Un cluster qui è "
        "semplicemente un **gruppo di comuni che si somigliano dal punto di "
        "vista climatico** — non un confine amministrativo o geografico, ma "
        "un raggruppamento calcolato guardando i numeri (temperatura media e "
        "quanti giorni all'anno superano 30°C/35°C). L'algoritmo usato, "
        "**K-means**, funziona così: si decide in anticipo **quanti gruppi si "
        "vogliono** (qui 3, una scelta pratica per avere poche zone facili da "
        "descrivere a parole — non calcolata con un metodo statistico che "
        "cerca il numero \"ottimale\"); poi l'algoritmo posiziona 3 centri "
        "provvisori, assegna ogni comune al centro più vicino guardando i suoi "
        "valori di temperatura/giorni caldi, sposta ogni centro sulla media "
        "dei comuni che gli sono stati assegnati, e ripete questi due passi "
        "finché i gruppi smettono di cambiare. Prima del calcolo i valori "
        "vengono **standardizzati** (riportati sulla stessa scala), altrimenti "
        "\"giorni sopra 30°C\" (che va da 0 a oltre 60) peserebbe molto più "
        "della temperatura media (che varia solo di pochi gradi) nel decidere "
        "la somiglianza. Importante: il raggruppamento **non guarda dove si "
        "trova un comune sulla mappa** — se i cluster risultano comunque "
        "geograficamente compatti (vicini fisicamente) è perché il clima "
        "reale del Piemonte è già organizzato per zone (montagna, pianura...), "
        "non perché l'algoritmo lo sappia in anticipo."
    )
    if spatial_df.empty:
        st.info("Esegui `python -m src.analysis.spatial_analysis` per generare questi risultati.")
    else:
        merged = geo_df.merge(spatial_df, on='municipality_name')
        col_map, col_info = st.columns([3, 2])
        with col_map:
            m3 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
            for _, row in merged.iterrows():
                color = CLUSTER_COLORS.get(int(row['climate_cluster']), '#95a5a6')
                folium.GeoJson(
                    wkt_to_geojson(row['geometry_wkt']),
                    tooltip=(
                        f"{row['municipality_name']} — cluster {int(row['climate_cluster'])}<br>"
                        f"Temp. media: {row['temp_mean_avg']:.1f}°C<br>"
                        f"Giorni >30°C: {row['days_gt_30c_avg']:.0f}/anno"
                    ),
                    style_function=lambda _, c=color: {'fillColor': c, 'color': c, 'fillOpacity': 0.6},
                ).add_to(m3)
            st_folium(m3, width=None, height=420, returned_objects=[], key='map_clusters')
        with col_info:
            st.markdown("**I 3 gruppi trovati oggi, dal più fresco al più caldo:**")
            cluster_summary = (
                merged.groupby('climate_cluster')
                .agg(temp=('temp_mean_avg', 'mean'), giorni_30=('days_gt_30c_avg', 'mean'), n=('municipality_name', 'count'))
                .sort_values('temp')
            )
            profile_labels = ["il più fresco", "un profilo intermedio", "il più caldo"]
            for rank, (cluster_id, stats) in enumerate(cluster_summary.iterrows()):
                group = merged[merged['climate_cluster'] == cluster_id]
                label = profile_labels[rank] if rank < len(profile_labels) else "un profilo a sé"
                st.markdown(
                    f"**Cluster {int(cluster_id)}** — {label} ({stats['temp']:.1f}°C medi, "
                    f"~{stats['giorni_30']:.0f} giorni/anno sopra 30°C, {int(stats['n'])} comuni): "
                    f"{', '.join(group['municipality_name'])}."
                )
            st.caption(
                "I comuni con temperatura/giorni caldi simili finiscono nello stesso gruppo "
                "indipendentemente da dove si trovano — che spesso coincidano con zone "
                "alpine, di pianura o intermedie è un risultato dell'analisi, non un'ipotesi "
                "di partenza."
            )

    st.subheader("Indice di Moran (autocorrelazione spaziale)")
    st.markdown(
        "**Cosa misura**: se i comuni **geograficamente vicini** hanno anche "
        "temperature **simili tra loro**, più di quanto ci si aspetterebbe se "
        "le temperature fossero distribuite a caso sulla mappa. Non è la "
        "stessa cosa dei cluster K-means sopra (quelli raggruppano per "
        "somiglianza climatica, senza guardare la posizione): l'indice di "
        "Moran guarda esplicitamente la **geografia**.\n\n"
        "**Come si calcola, in pratica**: per ogni comune si costruisce un "
        "peso che è tanto più alto quanto più un altro comune gli è vicino "
        "(l'inverso della distanza in km tra i due centri comunali) — comuni "
        "lontani pesano poco, comuni vicini pesano molto. L'indice combina "
        "questi pesi con quanto la temperatura di ciascun comune si discosta "
        "dalla media generale: se i comuni vicini tendono ad avere "
        "scostamenti dello **stesso segno** (tutti più caldi o tutti più "
        "freddi della media insieme), l'indice viene positivo e alto; se gli "
        "scostamenti dei vicini sono scollegati tra loro, l'indice si "
        "avvicina a zero.\n\n"
        "**Perché il p-value viene da una \"permutazione\" e non da una "
        "formula diretta**: si mescolano a caso le temperature tra i comuni "
        "(tenendo ferma la geografia) migliaia di volte, e si ricalcola "
        "l'indice ogni volta. Se il valore osservato con i dati veri è "
        "**più estremo** della quasi totalità di questi valori ottenuti "
        "mescolando a caso, allora il pattern geografico osservato è "
        "difficilmente dovuto al caso. Questo metodo è più affidabile della "
        "formula matematica classica quando, come qui, il numero di comuni "
        "non è enorme."
    )
    mi_df = get_morans_i_summary()
    if not mi_df.empty:
        mi = mi_df.iloc[0]
        d1, d2, d3 = st.columns(3)
        d1.metric("Moran's I", mi['morans_i'])
        d1.caption("Il valore osservato con i dati reali")
        d2.metric("Atteso sotto casualità", mi['expected_i_random'])
        d2.caption("Media dei valori ottenuti mescolando a caso")
        is_significant = mi['p_value_permutation'] < 0.05
        d3.metric("p-value (permutazione)", mi['p_value_permutation'])
        d3.caption("< 0.05 → pattern difficilmente casuale")
        if is_significant:
            st.success("Il caldo sembra concentrarsi in zone specifiche del Piemonte, non distribuirsi a caso.")
        else:
            st.info("Con questo campione non emerge un pattern geografico statisticamente chiaro.")

    st.subheader("Metodologia")
    st.markdown(
        "Alcune scelte fatte in questa pagina, spiegate:\n\n"
        "- **Perché proprio 3 fasce altitudinali, con quelle soglie?** "
        "Pianura/Collina/Montagna con soglie a 300 m e 700 m sono una "
        "semplificazione divulgativa basata sulla sola elevazione del "
        "centro di ciascun comune, non la classificazione ufficiale ISTAT "
        "di \"zona altimetrica\" (che è più complessa e valuta l'intero "
        "territorio comunale, non un solo punto). L'elevazione viene da "
        "Open-Meteo, non da un catasto ufficiale.\n"
        "- **Perché lo scatter uso del suolo/temperatura non è un vero "
        "studio dell'effetto isola di calore?** Mostra una correlazione tra "
        "tutti i comuni con dati, colorata per fascia altitudinale così da "
        "poter almeno *guardare a occhio* se l'effetto regge a parità di "
        "quota — ma il coefficiente di correlazione mostrato resta "
        "calcolato su tutti i comuni insieme, senza isolare "
        "matematicamente l'effetto della quota da quello dell'uso del "
        "suolo. Un modello che lo fa **esiste ora** "
        "(`src/analysis/spatial_regression.py`): OLS con "
        "elevazione+popolazione+%urbano+NDVI, seguito da un modello a "
        "errore spaziale dato che l'indice di Moran sui residui restava "
        "significativo (coerente con quello qui sotto). Risultato: "
        "l'effetto urbano diventa significativo col segno atteso solo nel "
        "modello spaziale — l'OLS classico lo mascherava. Vedi "
        "`wiki/pages/statistical-analysis.md`; risultato provvisorio, da "
        "confermare al crescere del campione di comuni.\n"
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
        "tempo. Un composito invernale darebbe una mappa molto diversa.\n"
        "- **Perché la mappa del trend non si aggiorna con il filtro anni?** "
        "Usa la pendenza di riscaldamento già calcolata sull'intero periodo "
        "disponibile per ciascun comune. Ricalcolarla ogni volta che cambi "
        "l'intervallo richiederebbe rileggere l'intera serie giornaliera di "
        "ogni comune a ogni interazione, troppo lento per una mappa "
        "interattiva — per questo resta un riferimento fisso, mentre la "
        "mappa della temperatura sopra si aggiorna regolarmente con il "
        "periodo scelto."
    )
