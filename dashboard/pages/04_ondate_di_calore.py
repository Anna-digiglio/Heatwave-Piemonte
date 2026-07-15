"""
04_ondate_di_calore.py - Frequenza, intensità, distribuzione geografica e
temporale delle ondate di calore.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from branca.colormap import LinearColormap
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from components.constants import TEMPERATURE_COLORSCALE
from components.filters import render_sidebar_filters
from components.heatwave_definitions import identify_heatwaves_percentile
from components.maps import wkt_to_geojson
from components.queries import (
    get_daily_temperature,
    get_heatwave_events,
    get_heatwave_frequency_by_year,
    get_heatwave_stats_by_municipality,
    get_municipality_geometries_wkt,
    get_municipality_metadata,
)
from components.styling import inject_custom_css

st.set_page_config(page_title='Ondate di Calore — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("🔥 Ondate di Calore")
st.caption("Quando, dove e quanto sono state intense le ondate di calore rilevate dal 2000 a oggi.")

year_start, year_end, provinces = render_sidebar_filters()

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Un'**ondata di calore** qui è definita come **almeno 3 giorni di fila** "
        "con temperatura massima sopra i **35°C**, la stessa soglia fissa per "
        "tutti i comuni (definizione usata in tutto il sito, calcolata dalla "
        "funzione `identify_heatwaves()` nel database). Per ogni ondata:\n\n"
        "- **Durata**: quanti giorni consecutivi è durata\n"
        "- **Intensità**: quanto la temperatura massima ha superato la soglia, "
        "moltiplicato per la durata\n\n"
        "Nel tab **Dettaglio tecnico** trovi anche un confronto con una "
        "definizione alternativa (soglia percentile, relativa al singolo comune "
        "invece che fissa per tutti)."
    )

metadata = get_municipality_metadata()
names_in_provinces = sorted(metadata[metadata['province_name'].isin(provinces)]['municipality_name'])

events_all = get_heatwave_events()
events = events_all[
    (events_all['start_date'].apply(lambda d: d.year) >= year_start)
    & (events_all['start_date'].apply(lambda d: d.year) <= year_end)
    & (events_all['municipality_name'].isin(names_in_provinces))
]

freq_df = get_heatwave_frequency_by_year()
freq_f = freq_df[(freq_df['year'] >= year_start) & (freq_df['year'] <= year_end)]

n_last_year = int(events[events['start_date'].apply(lambda d: d.year) == year_end].shape[0])

k1, k2, k3, k4 = st.columns(4)
k1.metric("N. ondate (periodo/filtro attuale)", len(events))
k1.caption(f"{year_start}-{year_end}, comuni filtrati")
k2.metric(f"N. ondate nel {year_end}", n_last_year)
k2.caption("Ultimo anno della finestra selezionata")
k3.metric("Durata media", f"{events['duration_days'].mean():.1f} gg" if not events.empty else "n/d")
k4.metric("Intensità media", f"{events['intensity_index'].mean():.1f}" if not events.empty else "n/d")
k4.caption("(Tmax - soglia) × durata")

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

with tab_overview:
    st.subheader("Frequenza e durata per anno")
    st.caption(
        "Barre = numero di ondate rilevate quell'anno (somma su tutti i comuni "
        "filtrati); linea = durata media in giorni. Guarda se le barre "
        "crescono negli anni recenti rispetto al primo decennio."
    )
    if freq_f.empty:
        st.info("Nessun dato per il periodo selezionato.")
    else:
        fig_freq = make_subplots(specs=[[{"secondary_y": True}]])
        fig_freq.add_trace(
            go.Bar(x=freq_f['year'], y=freq_f['n_heatwaves'], name='N. ondate', marker_color='#e74c3c'),
            secondary_y=False,
        )
        fig_freq.add_trace(
            go.Scatter(x=freq_f['year'], y=freq_f['avg_duration_days'], name='Durata media (gg)',
                       line=dict(color='#2c3e50', width=2)),
            secondary_y=True,
        )
        fig_freq.update_layout(height=350, margin=dict(t=10, b=10), legend=dict(orientation='h'))
        fig_freq.update_yaxes(title_text='N. ondate', secondary_y=False)
        fig_freq.update_yaxes(title_text='Durata media (gg)', secondary_y=True)
        st.plotly_chart(fig_freq, width='stretch')
        st.caption(
            "2003 e 2019 emergono come gli anni con più ondate, coerente con le "
            "note ondate di calore europee di quegli anni."
        )

    st.subheader("Intensità media per anno")
    st.caption(
        "Di quanto, in media, la temperatura massima ha superato la soglia dei "
        "35°C durante le ondate di ciascun anno (intensità più alta = ondate "
        "non solo più frequenti ma anche più estreme)."
    )
    if not freq_f.empty:
        fig_int = px.bar(
            freq_f, x='year', y='avg_intensity',
            labels={'year': 'Anno', 'avg_intensity': 'Intensità media'},
            color='avg_intensity', color_continuous_scale=TEMPERATURE_COLORSCALE,
        )
        fig_int.update_layout(height=300, margin=dict(t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig_int, width='stretch')

    st.subheader("Il fenomeno sta accelerando? Conteggio cumulato")
    st.caption(
        "Somma progressiva del numero di ondate dal 2000 in poi: se il "
        "fenomeno fosse costante nel tempo la linea sarebbe quasi dritta; se "
        "accelera, la linea si incurva verso l'alto negli anni recenti."
    )
    freq_cumulative = freq_df[freq_df['year'] <= year_end].copy()
    freq_cumulative['cumulato'] = freq_cumulative['n_heatwaves'].cumsum()
    fig_cum = px.line(
        freq_cumulative, x='year', y='cumulato',
        labels={'year': 'Anno', 'cumulato': 'N. ondate cumulate (dal 2000)'},
    )
    fig_cum.update_traces(line=dict(color='#e74c3c', width=3))
    fig_cum.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig_cum, width='stretch')

    st.subheader("Dove si concentrano geograficamente le ondate")
    st.caption("Colore più intenso = più ondate rilevate in quel comune (periodo/filtro attuale).")
    by_muni_full = get_heatwave_stats_by_municipality()
    events_count = events.groupby('municipality_name').size().rename('n_heatwaves_filtro').reset_index()
    geo_df = get_municipality_geometries_wkt()
    merged_geo = geo_df.merge(events_count, on='municipality_name', how='left')
    merged_geo['n_heatwaves_filtro'] = merged_geo['n_heatwaves_filtro'].fillna(0)

    if merged_geo.empty or merged_geo['n_heatwaves_filtro'].sum() == 0:
        st.info("Nessuna ondata nel periodo/filtro selezionato.")
    else:
        vmax = max(merged_geo['n_heatwaves_filtro'].max(), 1)
        cmap = LinearColormap(['#fee5d9', '#fb6a4a', '#a50f15'], vmin=0, vmax=vmax)
        m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles='CartoDB positron')
        for _, row in merged_geo.iterrows():
            color = cmap(row['n_heatwaves_filtro'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']}: {int(row['n_heatwaves_filtro'])} ondate",
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.8},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[], key='map_heatwave_concentration')

    st.subheader("Distribuzione nell'anno: si spostano verso primavera/autunno?")
    st.caption(
        "Ogni riga è un anno, ogni colonna un giorno dell'anno (1-365): il "
        "colore conta quanti comuni erano in un'ondata attiva quel giorno. "
        "Se col tempo compare colore fuori dalla fascia centrale (estate), "
        "è un indizio che le ondate si allargano verso primavera/autunno."
    )
    if events.empty:
        st.info("Nessuna ondata nel periodo/filtro selezionato.")
    else:
        expanded_rows = []
        for _, ev in events.iterrows():
            for day in pd.date_range(ev['start_date'], ev['end_date']):
                expanded_rows.append({'year': day.year, 'day_of_year': day.dayofyear})
        expanded = pd.DataFrame(expanded_rows)
        calendar_counts = expanded.groupby(['year', 'day_of_year']).size().rename('n').reset_index()
        pivot = calendar_counts.pivot(index='year', columns='day_of_year', values='n').fillna(0)
        fig_cal = px.imshow(
            pivot, aspect='auto', color_continuous_scale='YlOrRd',
            labels={'x': 'Giorno dell\'anno', 'y': 'Anno', 'color': 'N. comuni in ondata'},
        )
        fig_cal.update_layout(height=400, margin=dict(t=10, b=10))
        st.plotly_chart(fig_cal, width='stretch')

st.subheader("Statistiche per comune")
st.caption("Quale comune ha avuto più ondate, più lunghe, o più intense (su tutto il periodo 2000-2025)?")
by_muni = get_heatwave_stats_by_municipality()
by_muni_f = by_muni[by_muni['municipality_name'].isin(names_in_provinces)] if not by_muni.empty else by_muni
if by_muni_f.empty:
    st.info("Esegui `python -m src.analysis.heatwave_stats` per generare questi risultati.")
else:
    st.dataframe(
        by_muni_f.rename(columns={
            'municipality_name': 'Comune', 'n_heatwaves': 'N. ondate',
            'avg_duration_days': 'Durata media (gg)', 'max_duration_days': 'Durata max (gg)',
            'avg_intensity': 'Intensità media', 'max_intensity': 'Intensità max',
            'avg_max_temp': 'Temp. max media (°C)',
        }),
        hide_index=True, width='stretch',
    )

st.subheader("Elenco ondate")
st.caption("Ogni riga è una singola ondata di calore rilevata: data di inizio/fine, durata e temperature.")
st.dataframe(
    events.rename(columns={
        'municipality_name': 'Comune', 'province_name': 'Provincia',
        'start_date': 'Inizio', 'end_date': 'Fine', 'duration_days': 'Durata (gg)',
        'max_temp': 'Temp. max (°C)', 'mean_temp': 'Temp. media (°C)', 'intensity_index': 'Intensità',
    }),
    hide_index=True, width='stretch',
)

with tab_detail:
    st.subheader("Confronto con una definizione alternativa (soglia percentile)")
    st.caption(
        "La definizione canonica (35°C fissi) usa la stessa soglia per ogni "
        "comune. Un'alternativa comune in climatologia usa una soglia "
        "**relativa alla storia del singolo comune** (es. il suo 90° "
        "percentile di temperatura massima) — così anche un comune di "
        "montagna, che raramente tocca i 35°C, può avere le sue ondate "
        "rispetto ai propri standard locali."
    )
    municipality_detail = st.selectbox("Comune per il confronto", names_in_provinces or [""], key='detail_municipality')
    percentile = st.slider("Percentile soglia", 80, 99, 90, key='detail_percentile')

    if municipality_detail:
        daily = get_daily_temperature(municipality_detail)
        result = identify_heatwaves_percentile(daily, percentile=percentile)
        n_percentile = len(result['events'])
        n_fixed = len(events_all[events_all['municipality_name'] == municipality_detail])

        d1, d2, d3 = st.columns(3)
        d1.metric(f"Soglia percentile {percentile}°", f"{result['threshold']:.1f} °C")
        d2.metric("Ondate con soglia fissa (35°C)", n_fixed)
        d3.metric(f"Ondate con soglia percentile {percentile}°", n_percentile)
        st.caption(
            f"Per {municipality_detail}, il {percentile}° percentile storico di "
            f"temperatura massima è {result['threshold']:.1f}°C. Se questo valore "
            "è ben sotto i 35°C (tipico nei comuni di montagna), la definizione "
            "percentile trova più eventi locali di quella fissa."
        )

    st.subheader("Metodologia")
    st.markdown(
        "- **Definizione canonica** (usata ovunque nel resto del sito): "
        "`identify_heatwaves()` in `sql/01_init_database.sql` — almeno 3 "
        "giorni consecutivi con Tmax > 35°C, soglia fissa uguale per tutti "
        "i comuni.\n"
        "- **Definizione percentile** (solo qui, a scopo di confronto): "
        "`identify_heatwaves_percentile()` in "
        "`dashboard/components/heatwave_definitions.py` — stessa logica di "
        "sequenza minima di 3 giorni, ma soglia = percentile storico "
        "**del singolo comune**, non un numero fisso.\n"
        "- **Heatmap calendario**: aggrega tutte le ondate del filtro attuale "
        "per (anno, giorno dell'anno); un giorno con più comuni in ondata "
        "risulta più scuro."
    )
