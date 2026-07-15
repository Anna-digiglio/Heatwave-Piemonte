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

from components.constants import (
    CAPOLUOGHI, CLUSTER_COLORS, TEMPERATURE_COLORSCALE, TREND_COLORSCALE, elevation_band,
)
from components.filters import render_sidebar_filters
from components.maps import wkt_to_geojson
from components.queries import (
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

year_start, year_end, provinces = render_sidebar_filters()

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
        "anche temperature simili."
    )

st.info(
    "44 comuni con dati reali su 1180 totali (8 capoluoghi + 36 scelti per "
    "coprire il territorio). Le mappe provinciali aggregano solo i comuni "
    "disponibili in ciascuna provincia — vedi `wiki/pages/etl-pipeline.md`."
)

metadata = get_municipality_metadata()
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
k2.caption("Media dei comuni con dati nella provincia, 2000-2025")
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

        m1 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
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
    else:
        st.info("Nessun dato di temperatura per le province/periodo selezionati.")

    st.subheader("Velocità di riscaldamento per comune")
    st.caption(
        "Ogni punto è un comune, colorato per **pendenza del trend** "
        "(°C/decade, 2000-2025, non ricalcolato sul filtro anni — richiede la "
        "serie giornaliera completa). Rosso = si scalda più in fretta della "
        "media, blu = più lentamente. Il colore è centrato sullo zero: due "
        "sfumature di rosso diverse indicano comunque due velocità diverse "
        "di riscaldamento, non caldo/freddo assoluto."
    )
    geo_df = get_municipality_geometries_wkt()
    trend_points = trend_df.merge(geo_df, on='municipality_name').merge(
        metadata[['municipality_name', 'lat', 'lon']], on='municipality_name'
    )
    trend_points_f = trend_points[trend_points['province_name'].isin(provinces)]

    if trend_points_f.empty:
        st.info("Nessun comune con trend disponibile per il filtro scelto.")
    else:
        max_abs_slope = trend_points_f['lr_slope_per_decade'].abs().max() or 1
        cmap_trend = LinearColormap(
            ['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_slope, vmax=max_abs_slope
        )
        m2 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
        for _, row in trend_points_f.iterrows():
            color = cmap_trend(row['lr_slope_per_decade'])
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=7,
                color='#555', weight=1, fill=True, fill_color=color, fill_opacity=0.9,
                tooltip=f"{row['municipality_name']}: {row['lr_slope_per_decade']:+.2f} °C/decade",
            ).add_to(m2)
        st_folium(m2, width=None, height=420, returned_objects=[], key='map_trend_points')

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
        st.plotly_chart(fig_elev, width='stretch')

    st.subheader("Isola di calore urbana: Torino vs comuni rurali della provincia")
    st.caption(
        "Confronto tra la città di **Torino** e la media dei comuni rurali "
        "della sua stessa provincia (esclusi i capoluoghi) — se Torino risulta "
        "sistematicamente più calda, è un indizio dell'effetto \"isola di "
        "calore urbana\" (le città trattengono più calore di campagna/montagna)."
    )
    if 'Torino' not in provinces:
        st.info("Includi la provincia di Torino nel filtro sidebar per vedere questo confronto.")
    else:
        torino_prov_municipalities = metadata[metadata['province_name'] == 'Torino']['municipality_name']
        rural_names = [n for n in torino_prov_municipalities if n not in CAPOLUOGHI]
        annual_to = annual_f[annual_f['municipality_name'].isin(torino_prov_municipalities)]
        torino_series = annual_to[annual_to['municipality_name'] == 'Torino'].set_index('year')['temp_mean_annual']
        rural_series = annual_to[annual_to['municipality_name'].isin(rural_names)].groupby('year')['temp_mean_annual'].mean()

        if torino_series.empty or rural_series.empty:
            st.info("Dati insufficienti per il confronto nel periodo selezionato.")
        else:
            uhi_df = torino_series.rename('Torino (città)').to_frame().join(
                rural_series.rename('Media comuni rurali (provincia TO)'), how='inner'
            ).reset_index()
            fig_uhi = px.line(
                uhi_df, x='year', y=['Torino (città)', 'Media comuni rurali (provincia TO)'],
                labels={'year': 'Anno', 'value': 'Temp. media annuale (°C)', 'variable': ''},
                color_discrete_sequence=['#e74c3c', '#3498db'],
            )
            fig_uhi.update_layout(height=320, margin=dict(t=10, b=10), legend=dict(orientation='h'))
            st.plotly_chart(fig_uhi, width='stretch')
            diff = (uhi_df['Torino (città)'] - uhi_df['Media comuni rurali (provincia TO)']).mean()
            st.metric("Differenza media Torino vs rurale", f"{diff:+.1f} °C")

with tab_detail:
    spatial_df = get_spatial_analysis()
    geo_df = get_municipality_geometries_wkt()

    st.subheader("Cluster climatici (K-means, k=3)")
    st.caption(
        "Raggruppa i comuni in **zone climaticamente simili** guardando "
        "temperatura media e giorni di caldo intenso, con l'algoritmo "
        "**K-means** (mette nello stesso gruppo i comuni che si somigliano "
        "di più, senza confini decisi a priori)."
    )
    if spatial_df.empty:
        st.info("Esegui `python -m src.analysis.spatial_analysis` per generare questi risultati.")
    else:
        merged = geo_df.merge(spatial_df, on='municipality_name')
        col_map, col_info = st.columns([3, 2])
        with col_map:
            m3 = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
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
            for cluster_id, group in merged.groupby('climate_cluster'):
                st.markdown(
                    f"**Cluster {int(cluster_id)}** "
                    f"({', '.join(group['municipality_name'])}) — "
                    f"{group['temp_mean_avg'].mean():.1f}°C media"
                )

    st.subheader("Indice di Moran (autocorrelazione spaziale)")
    st.caption(
        "Un valore positivo e alto significa \"il caldo si concentra in zone "
        "precise\"; un valore vicino a zero (o negativo) significa \"non c'è "
        "un pattern geografico chiaro, sembra più casuale\"."
    )
    mi_df = get_morans_i_summary()
    if not mi_df.empty:
        mi = mi_df.iloc[0]
        d1, d2, d3 = st.columns(3)
        d1.metric("Moran's I", mi['morans_i'])
        d2.metric("Atteso sotto casualità", mi['expected_i_random'])
        is_significant = mi['p_value_permutation'] < 0.05
        d3.metric("p-value (permutazione)", mi['p_value_permutation'])
        if is_significant:
            st.success("Il caldo sembra concentrarsi in zone specifiche del Piemonte, non distribuirsi a caso.")
        else:
            st.info("Con questo campione non emerge un pattern geografico statisticamente chiaro.")

    st.subheader("Metodologia")
    st.markdown(
        "- **Fasce altitudinali**: soglie semplificate (300 m / 700 m) su "
        "elevazione del centroide comunale, non la classificazione ISTAT "
        "ufficiale di \"zona altimetrica\" (più complessa, per l'intero "
        "territorio comunale). Elevazione da Open-Meteo Elevation API "
        "(vedi `wiki/pages/data-sources.md`).\n"
        "- **Isola di calore urbana**: confronto illustrativo (media annuale "
        "Torino vs media dei comuni non-capoluogo della sua provincia), non "
        "un modello dell'effetto isola di calore in senso stretto (che "
        "richiederebbe stazioni urbane/rurali appaiate e controllate per "
        "quota/esposizione).\n"
        "- **Mappa del trend**: usa il coefficiente di regressione lineare "
        "precalcolato su tutto il periodo 2000-2025 (`trend_analysis.csv`), "
        "non ricalcolato sul filtro anni della sidebar (richiederebbe la "
        "serie giornaliera completa per ciascun comune ad ogni refresh)."
    )
