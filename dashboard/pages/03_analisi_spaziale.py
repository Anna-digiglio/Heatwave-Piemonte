"""
03_analisi_spaziale.py - Mappa dei cluster climatici + Moran's I.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import streamlit as st
from streamlit_folium import st_folium

from components.maps import wkt_to_geojson
from components.queries import (
    get_morans_i_summary,
    get_municipality_geometries_wkt,
    get_spatial_analysis,
)

st.set_page_config(page_title='Analisi Spaziale — Heatwave Piemonte', layout='wide')
st.title("🗺️ Analisi Spaziale")

st.warning(
    "Solo **8 unità spaziali** disponibili (i comuni capoluogo, unica "
    "granularità con temperature reali) — sotto la soglia comunemente "
    "considerata minima per un'analisi di autocorrelazione spaziale robusta. "
    "I risultati sotto sono illustrativi, non conclusivi. "
    "Vedi `wiki/pages/statistical-analysis.md` per il dettaglio."
)

spatial_df = get_spatial_analysis()
geo_df = get_municipality_geometries_wkt()

if spatial_df.empty:
    st.info("Esegui `python -m src.analysis.spatial_analysis` per generare questi risultati.")
else:
    merged = geo_df.merge(spatial_df, on='municipality_name')

    cluster_colors = {0: '#3498db', 1: '#e74c3c', 2: '#2ecc71', 3: '#f39c12'}

    col_map, col_info = st.columns([3, 2])

    with col_map:
        m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
        for _, row in merged.iterrows():
            color = cluster_colors.get(int(row['climate_cluster']), '#95a5a6')
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=(
                    f"{row['municipality_name']} — cluster {int(row['climate_cluster'])}<br>"
                    f"Temp. media: {row['temp_mean_avg']:.1f}°C<br>"
                    f"Giorni >30°C: {row['days_gt_30c_avg']:.0f}/anno"
                ),
                style_function=lambda _, c=color: {'fillColor': c, 'color': c, 'fillOpacity': 0.6},
            ).add_to(m)
        st_folium(m, width=None, height=500, returned_objects=[])

    with col_info:
        st.subheader("Cluster climatici (K-means, k=3)")
        for cluster_id, group in merged.groupby('climate_cluster'):
            st.markdown(
                f"**Cluster {int(cluster_id)}** "
                f"({', '.join(group['municipality_name'])}) — "
                f"{group['temp_mean_avg'].mean():.1f}°C media"
            )

        st.subheader("Indice di Moran (autocorrelazione spaziale)")
        mi_df = get_morans_i_summary()
        if not mi_df.empty:
            mi = mi_df.iloc[0]
            st.metric("Moran's I", mi['morans_i'])
            st.caption(
                f"Atteso sotto casualità: {mi['expected_i_random']} — "
                f"p-value (permutazione): {mi['p_value_permutation']} "
                f"({'significativo' if mi['p_value_permutation'] < 0.05 else 'non significativo'})"
            )
