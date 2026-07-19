"""
03_analisi_spaziale.py - Mappe coropletiche, trend per zona, fasce
altitudinali, isola di calore urbana, cluster climatici e Moran's I.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

from components.charts import apply_chart_theme
from components.constants import (
    CLUSTER_COLORS, MAP_TILES, TEMPERATURE_COLORSCALE, TREND_COLORSCALE, elevation_band,
)
from components.data_source import SOURCE_ARPA, SOURCE_BOTH, SOURCE_OPENMETEO, render_source_selector
from components.filters import render_province_filter, render_year_range_filter
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_arpa_hot_day_bias,
    get_arpa_kpi_annual,
    get_arpa_morans_i,
    get_arpa_municipality_geometries_wkt,
    get_arpa_municipality_metadata,
    get_arpa_spatial_clustering,
    get_arpa_trend_analysis,
    get_arpa_trend_comparison,
    get_arpa_validation,
    get_kpi_annual,
    get_kpi_annual_by_province,
    get_morans_i_summary,
    get_municipality_geometries_wkt,
    get_municipality_metadata,
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

metadata = get_municipality_metadata()
metadata_f = metadata[metadata['province_name'].isin(provinces)]
arpa_metadata = get_arpa_municipality_metadata()
arpa_metadata_f = arpa_metadata[arpa_metadata['province_name'].isin(provinces)]
names_in_provinces = sorted(metadata_f['municipality_name'])
names_in_provinces_arpa = sorted(arpa_metadata_f['municipality_name'])

source = render_source_selector(
    key='spaziale_source', has_om=bool(names_in_provinces), has_arpa=bool(names_in_provinces_arpa),
)
st.caption(
    "Il selettore sopra si applica alla mappa coropletica, alla mappa del trend, al confronto per "
    "fascia altitudinale, ai cluster climatici e all'indice di Moran."
)

active_metadata_f = arpa_metadata_f if source == SOURCE_ARPA else metadata_f
active_names = names_in_provinces_arpa if source == SOURCE_ARPA else names_in_provinces

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
        "- Per le mappe di **uso del suolo**, **densità di popolazione** e "
        "**NDVI** (che coprono tutti i 1180 comuni piemontesi, non solo "
        "quelli con temperatura) vedi la pagina Contesto Territoriale "
        "(link sotto)."
    )

st.info(
    f"{len(metadata)} comuni con dati Open-Meteo su 1180 totali (8 capoluoghi + "
    f"{len(metadata) - 8} scelti per coprire il territorio); {len(arpa_metadata)} "
    "con dati ARPA (stazione reale). Le mappe provinciali aggregano solo i comuni "
    "disponibili in ciascuna provincia."
)
st.page_link("pages/05_contesto_territoriale.py", label="Uso del suolo, popolazione e NDVI → Contesto Territoriale")

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

# --- Dati aggregati per provincia, filtrati per periodo -------------------
# Fonte Open-Meteo: vista materializzata + CSV precalcolato. Fonte ARPA:
# nessuna vista/CSV equivalente, calcolati al volo con lo stesso metodo
# (vedi get_arpa_kpi_annual()/get_arpa_trend_analysis() in queries.py).
if source == SOURCE_ARPA:
    kpi_active = get_arpa_kpi_annual().merge(
        arpa_metadata[['municipality_name', 'province_name']], on='municipality_name'
    )
    kpi_active_f = kpi_active[
        (kpi_active['year'] >= year_start) & (kpi_active['year'] <= year_end)
        & (kpi_active['province_name'].isin(provinces))
    ]
    province_avg = kpi_active_f.groupby('province_name').agg(
        temp_mean_annual=('temp_mean_annual', 'mean'),
        days_gt_30c=('days_gt_30c', 'mean'),
    ).reset_index()
    trend_df = get_arpa_trend_analysis()
    trend_with_province = trend_df.merge(
        arpa_metadata[['municipality_name', 'province_name']], on='municipality_name'
    )
else:
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

top_elev = (
    active_metadata_f.loc[active_metadata_f['elevation_m'].idxmax()]
    if not active_metadata_f.empty and active_metadata_f['elevation_m'].notna().any() else None
)

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
k4.metric("Comuni con dati (filtro attuale)", len(active_metadata_f))
k4.caption(f"Su {len(arpa_metadata) if source == SOURCE_ARPA else len(metadata)} comuni totali con dati {('ARPA' if source == SOURCE_ARPA else 'Open-Meteo')}")

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

    def render_trend_map(points_df: pd.DataFrame, cmap, map_key: str) -> None:
        m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
        for _, row in points_df.iterrows():
            color = cmap(row['lr_slope_per_decade'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']}: {row['lr_slope_per_decade']:+.2f} °C/decade",
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 0.5, 'fillOpacity': 0.85},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[], key=map_key)

    st.subheader("Velocità di riscaldamento per comune")
    st.caption(
        "Ogni comune è colorato per **pendenza del trend** (°C/decade, intero "
        "periodo disponibile, non ricalcolato sul filtro anni — richiede la "
        "serie giornaliera completa). Rosso = si scalda più in fretta della "
        "media, blu = più lentamente. Il colore è centrato sullo zero: due "
        "sfumature di rosso diverse indicano comunque due velocità diverse "
        "di riscaldamento, non caldo/freddo assoluto."
    )

    if source == SOURCE_BOTH:
        trend_om_f = get_trend_analysis().merge(
            get_municipality_geometries_wkt(), on='municipality_name'
        )
        trend_om_f = trend_om_f[trend_om_f['province_name'].isin(provinces)]
        trend_arpa_f = get_arpa_trend_analysis().merge(
            get_arpa_municipality_geometries_wkt(), on='municipality_name'
        )
        trend_arpa_f = trend_arpa_f[trend_arpa_f['province_name'].isin(provinces)]

        if trend_om_f.empty and trend_arpa_f.empty:
            st.info("Nessun comune con trend disponibile per il filtro scelto.")
        else:
            # Stessa scala colore per le due mappe (max assoluto tra le due
            # fonti), altrimenti un rosso identico potrebbe rappresentare
            # velocità di riscaldamento diverse da una mappa all'altra.
            max_abs_slope = max(
                trend_om_f['lr_slope_per_decade'].abs().max() if not trend_om_f.empty else 0,
                trend_arpa_f['lr_slope_per_decade'].abs().max() if not trend_arpa_f.empty else 0,
            ) or 1
            cmap_trend = LinearColormap(['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_slope, vmax=max_abs_slope)

            col_om, col_arpa = st.columns(2)
            with col_om:
                st.markdown(f"**Open-Meteo** ({len(trend_om_f)} comuni)")
                render_trend_map(trend_om_f, cmap_trend, 'map_trend_points_om')
            with col_arpa:
                st.markdown(f"**ARPA — stazione reale** ({len(trend_arpa_f)} comuni)")
                render_trend_map(trend_arpa_f, cmap_trend, 'map_trend_points_arpa')

            render_gradient_legend(
                cmap_trend, -max_abs_slope, max_abs_slope,
                labels=["Raffreddamento", "Riscaldamento lento", "Riscaldamento moderato",
                        "Riscaldamento sostenuto", "Riscaldamento rapido"],
                unit="°C/decade", title="Legenda — velocità di riscaldamento (stessa scala per entrambe le mappe)",
                signed=True,
            )
            st.caption(
                "Le due mappe non coprono esattamente gli stessi comuni (108 hanno "
                "entrambe le fonti, gli altri solo una — vedi info box in alto): "
                "confronta le zone dove **entrambe** hanno un colore, non l'assenza "
                "di colore in una delle due."
            )
    else:
        geo_df_active = get_arpa_municipality_geometries_wkt() if source == SOURCE_ARPA else get_municipality_geometries_wkt()
        trend_points = trend_df.merge(geo_df_active, on='municipality_name')
        trend_points_f = trend_points[trend_points['province_name'].isin(provinces)]

        if trend_points_f.empty:
            st.info("Nessun comune con trend disponibile per il filtro scelto.")
        else:
            max_abs_slope = trend_points_f['lr_slope_per_decade'].abs().max() or 1
            cmap_trend = LinearColormap(
                ['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_slope, vmax=max_abs_slope
            )
            render_trend_map(trend_points_f, cmap_trend, 'map_trend_points')
            render_gradient_legend(
                cmap_trend, -max_abs_slope, max_abs_slope,
                labels=["Raffreddamento", "Riscaldamento lento", "Riscaldamento moderato",
                        "Riscaldamento sostenuto", "Riscaldamento rapido"],
                unit="°C/decade", title="Legenda — velocità di riscaldamento", signed=True,
            )

    if source == SOURCE_BOTH:
        st.subheader("Bias Open-Meteo vs ARPA per comune")
        st.caption(
            "A differenza delle due mappe sopra (ciascuna fonte calcola il proprio trend in "
            "autonomia), questa mappa mostra la differenza **diretta** giorno per giorno tra le "
            "due fonti sullo stesso comune (Open-Meteo − ARPA su temp. massima) — per questo "
            "esiste solo per i 108 comuni con **entrambe** le fonti, non per i 110 solo-ARPA. "
            "Blu = Open-Meteo sottostima la temperatura reale (la maggioranza dei casi)."
        )
        validation = get_arpa_validation()
        bias_points = validation.merge(get_municipality_geometries_wkt(), on='municipality_name')
        bias_points_f = bias_points[bias_points['province_name'].isin(provinces)]

        if bias_points_f.empty:
            st.info("Nessun comune con validazione ARPA disponibile per il filtro scelto.")
        else:
            max_abs_bias = bias_points_f['temp_max_bias'].abs().max() or 1
            cmap_bias = LinearColormap(['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_bias, vmax=max_abs_bias)
            m_bias = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
            for _, row in bias_points_f.iterrows():
                color = cmap_bias(row['temp_max_bias'])
                folium.GeoJson(
                    wkt_to_geojson(row['geometry_wkt']),
                    tooltip=(
                        f"{row['municipality_name']}: bias {row['temp_max_bias']:+.2f}°C, "
                        f"r={row['temp_max_r']:.3f} (stazione: {row['station_name']})"
                    ),
                    style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.85},
                ).add_to(m_bias)
            st_folium(m_bias, width=None, height=420, returned_objects=[], key='map_arpa_bias_spatial')
            render_gradient_legend(
                cmap_bias, -max_abs_bias, max_abs_bias,
                labels=["Sottostima forte", "Sottostima lieve", "Accurato", "Sovrastima lieve", "Sovrastima forte"],
                unit="°C", title="Legenda — bias Open-Meteo vs ARPA", signed=True,
            )

    st.subheader("Temperatura per fascia altitudinale")
    st.caption(
        "I comuni sono divisi in 3 fasce in base all'elevazione del loro "
        "centroide: **Pianura** (<300 m), **Collina** (300-700 m), "
        "**Montagna** (>700 m). Il grafico mostra quanto la quota fa "
        "davvero la differenza sulla temperatura media."
    )
    # `annual`/`annual_f` restano Open-Meteo: servono anche più sotto per lo
    # scatter uso del suolo/popolazione, che non risponde al selettore fonte
    # (vedi caption in alto). Per il grafico qui sotto, `annual_elev` usa
    # invece la fonte attiva.
    annual = get_kpi_annual()
    annual_f = annual[(annual['year'] >= year_start) & (annual['year'] <= year_end)]
    if source == SOURCE_ARPA:
        annual_active = get_arpa_kpi_annual()
        annual_active_f = annual_active[(annual_active['year'] >= year_start) & (annual_active['year'] <= year_end)]
        annual_elev = annual_active_f.merge(arpa_metadata_f[['municipality_name', 'elevation_m']], on='municipality_name')
    else:
        annual_elev = annual_f.merge(metadata_f[['municipality_name', 'elevation_m']], on='municipality_name')

    if annual_elev.empty:
        st.info("Nessun dato di elevazione disponibile per il filtro scelto.")
    else:
        annual_elev = annual_elev.copy()
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

    if source == SOURCE_BOTH:
        arpa_annual_active = get_arpa_kpi_annual()
        arpa_annual_active_f = arpa_annual_active[
            (arpa_annual_active['year'] >= year_start) & (arpa_annual_active['year'] <= year_end)
        ]
        annual_elev_arpa = arpa_annual_active_f.merge(
            arpa_metadata_f[['municipality_name', 'elevation_m']], on='municipality_name'
        )
        if not annual_elev.empty and not annual_elev_arpa.empty:
            annual_elev_arpa = annual_elev_arpa.copy()
            annual_elev_arpa['fascia'] = annual_elev_arpa['elevation_m'].apply(elevation_band)
            comparison_fascia = pd.DataFrame({
                'Open-Meteo': annual_elev.groupby('fascia')['temp_mean_annual'].mean(),
                'ARPA': annual_elev_arpa.groupby('fascia')['temp_mean_annual'].mean(),
            }).reindex(['Pianura', 'Collina', 'Montagna'])
            comparison_fascia['Bias (OM − ARPA)'] = comparison_fascia['Open-Meteo'] - comparison_fascia['ARPA']
            st.caption(
                "**Confronto ARPA vs Open-Meteo per fascia altitudinale** — la stessa "
                "quota media, calcolata sulle due fonti separatamente: se il bias "
                "cresce salendo da Pianura a Montagna, conferma che Open-Meteo "
                "sottostima di più in quota (coerente con la validazione — vedi \"Validazione "
                "ARPA — dettaglio\" nel tab Dettaglio tecnico)."
            )
            st.dataframe(
                comparison_fascia.style.format({
                    'Open-Meteo': '{:.2f}', 'ARPA': '{:.2f}', 'Bias (OM − ARPA)': '{:+.2f}',
                }),
                width='stretch',
            )

    st.caption(
        "Le mappe di uso del suolo, densità di popolazione e NDVI (tutti i 1180 comuni "
        "piemontesi) e il confronto diretto con la temperatura sono nella pagina "
        "Contesto Territoriale:"
    )
    st.page_link("pages/05_contesto_territoriale.py", label="🌍 Vai a Contesto Territoriale →")

with tab_detail:
    # Cluster/Moran's I sono calcolati sull'intero periodo/tutti i comuni
    # della fonte attiva (non filtrati per anno/provincia, come già era per
    # Open-Meteo) - in modalità "Confronto" restano su Open-Meteo, stessa
    # convenzione usata per le sezioni sopra.
    if source == SOURCE_ARPA:
        spatial_df = get_arpa_spatial_clustering()
        geo_df = get_arpa_municipality_geometries_wkt()
    else:
        spatial_df = get_spatial_analysis()
        geo_df = get_municipality_geometries_wkt()

    if source != SOURCE_OPENMETEO:
        st.caption(
            f"Cluster e indice di Moran sotto calcolati su "
            f"{'ARPA (stazione reale)' if source == SOURCE_ARPA else 'Open-Meteo — il confronto resta su Open-Meteo anche in modalità Confronto'}."
        )

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
        st.info("Dati dei cluster climatici non ancora disponibili.")
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
    if source == SOURCE_ARPA:
        mi = get_arpa_morans_i()
    else:
        mi_df = get_morans_i_summary()
        mi = mi_df.iloc[0].to_dict() if not mi_df.empty else {}
    if mi:
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

    if source == SOURCE_BOTH:
        st.subheader("Validazione ARPA — dettaglio")
        st.caption(
            "Ex pagina dedicata \"Validazione Dati\", spostata qui il 2026-07-18: la mappa bias "
            "e il confronto ondate/trend sono già più sopra e in Ondate di Calore/Analisi "
            "Temporale (modalità Confronto) — qui il resto del dettaglio, sui 108 comuni con "
            "entrambe le fonti."
        )
        validation = get_arpa_validation()
        hot_bias = get_arpa_hot_day_bias()
        trend_comparison = get_arpa_trend_comparison()

        if validation.empty:
            st.info("Dati di validazione ARPA non ancora disponibili.")
        else:
            validation_elev = validation.merge(
                metadata[['municipality_name', 'elevation_m']], on='municipality_name', how='left'
            )
            col_scatter1, col_scatter2 = st.columns(2)
            with col_scatter1:
                st.markdown("**Bias vs elevazione**")
                st.caption(
                    "Più alto il comune, più Open-Meteo tende a sottostimare le massime reali "
                    "(r=-0.35, p=0.012) — coerente con un prodotto di rianalisi che media una "
                    "cella di griglia, non un punto, in rilievo alpino complesso."
                )
                fig_bias_elev = px.scatter(
                    validation_elev, x='elevation_m', y='temp_max_bias', hover_name='municipality_name',
                    labels={'temp_max_bias': 'Bias temp. massima (°C)', 'elevation_m': 'Elevazione comune (m)'},
                    trendline='ols',
                )
                fig_bias_elev.add_hline(y=0, line_dash='dash', line_color='gray')
                st.plotly_chart(apply_chart_theme(fig_bias_elev), width='stretch')
            with col_scatter2:
                st.markdown(f"**Distribuzione del bias sui {len(validation)} comuni**")
                st.caption("La maggior parte dei comuni ha bias negativo (Open-Meteo sottostima).")
                fig_bias_hist = px.histogram(
                    validation, x='temp_max_bias', nbins=20,
                    labels={'temp_max_bias': 'Bias temp. massima (°C)'},
                )
                fig_bias_hist.add_vline(x=0, line_dash='dash', line_color='gray')
                fig_bias_hist.add_vline(x=validation['temp_max_bias'].mean(), line_color='#e74c3c', annotation_text='media')
                st.plotly_chart(apply_chart_theme(fig_bias_hist), width='stretch')

            if not hot_bias.empty:
                st.markdown("**Bias sui giorni davvero caldi**")
                st.caption(
                    "Il bias sopra è calcolato su tutti i giorni dell'anno — qui ristretto ai giorni "
                    "con temperatura ARPA (verità di terra) sopra soglia. Il bias resta simile, ma "
                    "la correlazione crolla: Open-Meteo perde la capacità di distinguere quali "
                    "giorni estremi lo sono davvero di più."
                )
                st.dataframe(
                    hot_bias.rename(columns={
                        'condition': 'Condizione', 'n_days': 'Giorni', 'bias': 'Bias (°C)',
                        'mae': 'MAE (°C)', 'rmse': 'RMSE (°C)', 'r': 'Correlazione (r)', 'r_p_value': 'p-value',
                    }),
                    width='stretch', hide_index=True,
                )

            st.markdown("**Tabella completa per comune**")
            display_cols = [c for c in [
                'municipality_name', 'station_name', 'temp_max_n_days', 'temp_max_bias',
                'temp_max_mae', 'temp_max_rmse', 'temp_max_r',
            ] if c in validation.columns]
            st.dataframe(
                validation[display_cols].sort_values('temp_max_bias').rename(columns={
                    'municipality_name': 'Comune', 'station_name': 'Stazione ARPA',
                    'temp_max_n_days': 'Giorni confrontati', 'temp_max_bias': 'Bias (°C)',
                    'temp_max_mae': 'MAE (°C)', 'temp_max_rmse': 'RMSE (°C)', 'temp_max_r': 'Correlazione (r)',
                }),
                width='stretch', hide_index=True,
            )

            if not trend_comparison.empty:
                st.markdown("**Trend di riscaldamento: regge sui dati di stazione reali?**")
                st.caption(
                    "A differenza del conteggio delle ondate, il trend di riscaldamento "
                    "(Mann-Kendall + regressione lineare) è risultato robusto alla fonte dati: il "
                    "segno della pendenza concorda tra ARPA e Open-Meteo nell'88% dei comuni, e "
                    "nessun comune mostra trend opposti *entrambi* statisticamente significativi."
                )
                both_sources = trend_comparison.dropna(subset=['om_slope_per_decade'])
                display_cols_t = [c for c in [
                    'municipality_name', 'arpa_slope_per_decade', 'arpa_mk_p_value',
                    'om_slope_per_decade', 'om_mk_p_value',
                ] if c in both_sources.columns]
                st.dataframe(
                    both_sources[display_cols_t].rename(columns={
                        'municipality_name': 'Comune', 'arpa_slope_per_decade': 'Pendenza ARPA (°C/decade)',
                        'arpa_mk_p_value': 'p-value ARPA', 'om_slope_per_decade': 'Pendenza Open-Meteo (°C/decade)',
                        'om_mk_p_value': 'p-value Open-Meteo',
                    }),
                    width='stretch', hide_index=True,
                )

            st.caption(
                "**Metodologia validazione**: fonte ARPA Piemonte (rete di stazioni meteo "
                "ufficiali della regione); quando un comune ha più stazioni attive si sceglie "
                "quella con quota più vicina al comune; bias/MAE/RMSE/correlazione calcolati su "
                "tutte le coppie (comune, data) disponibili in entrambe le fonti, 2000-oggi. "
                "**Caveat**: la stazione scelta non è necessariamente rappresentativa dell'intero "
                "territorio comunale, specie nei comuni alpini estesi dove può essere un rifugio a "
                "quota molto diversa dal fondovalle abitato."
            )

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
        "- Lo scatter uso del suolo/popolazione/NDVI vs temperatura, e il "
        "modello di regressione spaziale che lo accompagna, sono nella pagina "
        "Contesto Territoriale — insieme ai limiti delle fonti CORINE Land "
        "Cover e NDVI usate lì.\n"
        "- **Perché la mappa del trend non si aggiorna con il filtro anni?** "
        "Usa la pendenza di riscaldamento già calcolata sull'intero periodo "
        "disponibile per ciascun comune. Ricalcolarla ogni volta che cambi "
        "l'intervallo richiederebbe rileggere l'intera serie giornaliera di "
        "ogni comune a ogni interazione, troppo lento per una mappa "
        "interattiva — per questo resta un riferimento fisso, mentre la "
        "mappa della temperatura sopra si aggiorna regolarmente con il "
        "periodo scelto."
    )
