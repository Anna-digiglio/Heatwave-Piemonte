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
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from components.charts import apply_chart_theme
from components.constants import MAP_TILES, TEMPERATURE_COLORSCALE
from components.data_source import SOURCE_ARPA, SOURCE_BOTH, SOURCE_OPENMETEO, render_source_selector
from components.filters import render_province_filter, render_year_range_filter
from components.heatwave_definitions import identify_heatwaves_percentile
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    compute_frequency_by_year,
    compute_stats_by_municipality,
    get_arpa_daily_temperature,
    get_arpa_event_comparison_summary,
    get_arpa_heatwave_events,
    get_arpa_municipality_geometries_wkt,
    get_arpa_municipality_metadata,
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

col_year, col_prov = st.columns(2)
with col_year:
    year_start, year_end = render_year_range_filter(key='ondate_year_range')
with col_prov:
    provinces = render_province_filter(key='ondate_province')
st.caption("Entrambi i filtri sopra si applicano a tutti i grafici, la mappa e le tabelle di questa pagina.")

metadata = get_municipality_metadata()
names_in_provinces = sorted(metadata[metadata['province_name'].isin(provinces)]['municipality_name'])
arpa_metadata = get_arpa_municipality_metadata()
names_in_provinces_arpa = sorted(arpa_metadata[arpa_metadata['province_name'].isin(provinces)]['municipality_name'])

source = render_source_selector(
    key='ondate_source', has_om=bool(names_in_provinces), has_arpa=bool(names_in_provinces_arpa),
)
if source == SOURCE_ARPA:
    st.caption(
        f"Fonte **ARPA** (stazioni reali): {len(names_in_provinces_arpa)} comuni con dati nel "
        "filtro attuale — un insieme diverso da quello Open-Meteo, non necessariamente sovrapposto."
    )
elif source == SOURCE_BOTH:
    st.caption(
        "Grafici e tabelle sotto restano calcolati su Open-Meteo (il pannello di confronto qui "
        "sotto aggiunge le metriche di validazione contro ARPA); la mappa di concentrazione più "
        "in basso è l'eccezione — mostra due mappe affiancate, una per fonte."
    )

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Un'**ondata di calore** qui è definita come **almeno 3 giorni di fila** "
        "con temperatura massima sopra i **35°C**, la stessa soglia fissa per "
        "tutti i comuni (definizione usata in tutto il sito, calcolata dalla "
        "funzione `identify_heatwaves()` nel database) — una scelta "
        "semplificata: i climatologi usano spesso soglie che variano da "
        "località a località, non un valore fisso, ma qui si è preferita "
        "una definizione facile da capire e da verificare. Per ogni ondata:\n\n"
        "- **Durata**: quanti giorni consecutivi è durata\n"
        "- **Intensità**: quanto la temperatura massima ha superato la soglia, "
        "moltiplicato per la durata\n\n"
        "Nel tab **Dettaglio tecnico** trovi anche un confronto con una "
        "definizione alternativa (soglia percentile, relativa al singolo comune "
        "invece che fissa per tutti)."
    )

active_names = names_in_provinces_arpa if source == SOURCE_ARPA else names_in_provinces

if source == SOURCE_ARPA:
    events_all = get_arpa_heatwave_events(tuple(names_in_provinces_arpa))
else:
    events_all = get_heatwave_events()

events = events_all[
    (events_all['start_date'].apply(lambda d: d.year) >= year_start)
    & (events_all['start_date'].apply(lambda d: d.year) <= year_end)
    & (events_all['municipality_name'].isin(active_names))
]

freq_df = compute_frequency_by_year(events_all) if source == SOURCE_ARPA else get_heatwave_frequency_by_year()
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

if source == SOURCE_BOTH:
    comparison = get_arpa_event_comparison_summary()
    if comparison:
        st.subheader("Confronto ARPA vs Open-Meteo — quante ondate reali vengono rilevate?")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Recall (su ondate ARPA reali)", f"{comparison.get('recall', float('nan')):.1%}")
        cc1.caption("Quota di ondate ARPA reali anche rilevate da Open-Meteo")
        cc2.metric("Precision", f"{comparison.get('precision', float('nan')):.1%}")
        cc2.caption("Quota di ondate Open-Meteo confermate anche da ARPA")
        cc3.metric("Ondate ARPA reali", int(comparison.get('n_arpa_events', 0)))
        cc3.caption(f"Contro {int(comparison.get('n_om_events', 0))} rilevate da Open-Meteo")
        st.caption(
            "Calcolato sui 51 comuni con entrambe le fonti (non filtrato per provincia/anno — "
            "vedi src/analysis/validate_arpa.py)."
        )
    else:
        st.info("Nessun risultato di confronto trovato: esegui `python -m src.analysis.validate_arpa`.")

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
        st.plotly_chart(apply_chart_theme(fig_freq), width='stretch')
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
        vmax_intensity = max(freq_f['avg_intensity'].max(), 1)
        fig_int = px.bar(
            freq_f, x='year', y='avg_intensity',
            labels={'year': 'Anno', 'avg_intensity': 'Intensità media'},
            color='avg_intensity', color_continuous_scale=TEMPERATURE_COLORSCALE,
            range_color=(0, vmax_intensity),
        )
        fig_int.update_layout(height=300, margin=dict(t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(apply_chart_theme(fig_int), width='stretch')

        def _intensity_colormap(value, _vmax=vmax_intensity):
            norm = max(0.0, min(1.0, value / _vmax))
            return sample_colorscale(TEMPERATURE_COLORSCALE, [norm])[0]

        render_gradient_legend(
            _intensity_colormap, 0, vmax_intensity,
            labels=["Bassa", "Moderata", "Alta", "Molto alta", "Estrema"],
            unit="", title="Legenda — intensità media",
        )

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
    st.plotly_chart(apply_chart_theme(fig_cum), width='stretch')

    def render_concentration_map(merged_geo: pd.DataFrame, cmap, map_key: str) -> None:
        m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
        for _, row in merged_geo.iterrows():
            color = cmap(row['n_heatwaves_filtro'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=f"{row['municipality_name']}: {int(row['n_heatwaves_filtro'])} ondate",
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.8},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[], key=map_key)

    def count_events_by_municipality(events_df: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
        counts = events_df.groupby('municipality_name').size().rename('n_heatwaves_filtro').reset_index()
        merged = geo.merge(counts, on='municipality_name', how='left')
        merged['n_heatwaves_filtro'] = merged['n_heatwaves_filtro'].fillna(0)
        return merged

    st.subheader("Dove si concentrano geograficamente le ondate")
    st.caption("Colore più intenso = più ondate rilevate in quel comune (periodo/filtro attuale).")

    if source == SOURCE_BOTH:
        events_arpa_all = get_arpa_heatwave_events(tuple(names_in_provinces_arpa))
        events_arpa_f = events_arpa_all[
            (events_arpa_all['start_date'].apply(lambda d: d.year) >= year_start)
            & (events_arpa_all['start_date'].apply(lambda d: d.year) <= year_end)
        ] if not events_arpa_all.empty else events_arpa_all

        merged_om = count_events_by_municipality(events, get_municipality_geometries_wkt())
        merged_arpa = count_events_by_municipality(events_arpa_f, get_arpa_municipality_geometries_wkt())

        if merged_om['n_heatwaves_filtro'].sum() == 0 and merged_arpa['n_heatwaves_filtro'].sum() == 0:
            st.info("Nessuna ondata nel periodo/filtro selezionato.")
        else:
            # Stessa scala colore per le due mappe (max assoluto tra le due
            # fonti), altrimenti lo stesso rosso potrebbe rappresentare
            # conteggi diversi da una mappa all'altra.
            vmax = max(merged_om['n_heatwaves_filtro'].max(), merged_arpa['n_heatwaves_filtro'].max(), 1)
            cmap = LinearColormap(['#fee5d9', '#fb6a4a', '#a50f15'], vmin=0, vmax=vmax)

            col_om, col_arpa = st.columns(2)
            with col_om:
                st.markdown(f"**Open-Meteo** ({int(merged_om['n_heatwaves_filtro'].sum())} ondate)")
                render_concentration_map(merged_om, cmap, 'map_heatwave_concentration_om')
            with col_arpa:
                st.markdown(f"**ARPA — stazione reale** ({int(merged_arpa['n_heatwaves_filtro'].sum())} ondate)")
                render_concentration_map(merged_arpa, cmap, 'map_heatwave_concentration_arpa')

            render_gradient_legend(
                cmap, 0, vmax,
                labels=["Poche", "Basso", "Moderato", "Alto", "Molto alto"],
                unit="ondate", title="Legenda — concentrazione ondate (stessa scala per entrambe le mappe)",
                integer=True,
            )
            st.caption(
                "Le due mappe non coprono esattamente gli stessi comuni (51 hanno entrambe le "
                "fonti, gli altri solo una): confronta le zone dove **entrambe** hanno un colore, "
                "non l'assenza di colore in una delle due."
            )
    else:
        geo_df = get_arpa_municipality_geometries_wkt() if source == SOURCE_ARPA else get_municipality_geometries_wkt()
        merged_geo = count_events_by_municipality(events, geo_df)

        if merged_geo.empty or merged_geo['n_heatwaves_filtro'].sum() == 0:
            st.info("Nessuna ondata nel periodo/filtro selezionato.")
        else:
            vmax = max(merged_geo['n_heatwaves_filtro'].max(), 1)
            cmap = LinearColormap(['#fee5d9', '#fb6a4a', '#a50f15'], vmin=0, vmax=vmax)
            render_concentration_map(merged_geo, cmap, 'map_heatwave_concentration')
            render_gradient_legend(
                cmap, 0, vmax,
                labels=["Poche", "Basso", "Moderato", "Alto", "Molto alto"],
                unit="ondate", title="Legenda — concentrazione ondate", integer=True,
            )

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
        st.plotly_chart(apply_chart_theme(fig_cal), width='stretch')

st.subheader("Statistiche per comune")
st.caption("Quale comune ha avuto più ondate, più lunghe, o più intense (su tutto il periodo disponibile)?")
by_muni = compute_stats_by_municipality(events_all) if source == SOURCE_ARPA else get_heatwave_stats_by_municipality()
by_muni_f = by_muni[by_muni['municipality_name'].isin(active_names)] if not by_muni.empty else by_muni
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
    st.markdown(
        "**Perché una definizione alternativa?** La soglia fissa di 35°C usata "
        "in tutto il resto del sito è facile da capire, ma tratta tutti i "
        "comuni allo stesso modo: un comune di montagna che non arriva quasi "
        "mai a 35°C non registrerà quasi mai un'ondata con questa regola, "
        "anche in un'estate eccezionalmente calda **per i suoi standard**. "
        "Un'alternativa comune in climatologia è usare una soglia diversa per "
        "ogni comune, calcolata sulla **sua** storia invece che un numero "
        "uguale per tutti.\n\n"
        "**Cos'è un \"percentile\" e come si calcola qui**: prendi tutte le "
        "temperature massime giornaliere mai registrate in un comune (26 anni "
        "di dati) e ordinale dalla più bassa alla più alta. Il **90° "
        "percentile** è il valore sotto il quale si trova il 90% di quei "
        "giorni — cioè la soglia superata solo nel 10% delle giornate più "
        "calde mai registrate lì. Cambiando lo slider sotto puoi rendere la "
        "soglia più severa (percentile più alto, es. 99° = solo l'1% dei "
        "giorni più estremi) o più permissiva (percentile più basso). A "
        "differenza dei 35°C fissi, questo numero è **diverso per ogni "
        "comune**: per un comune di pianura può risultare vicino ai 35°C "
        "originali, per un comune di montagna sarà molto più basso, perché "
        "riflette cosa è davvero \"eccezionale\" lì."
    )
    municipality_detail = st.selectbox("Comune per il confronto", active_names or [""], key='detail_municipality')
    percentile = st.slider("Percentile soglia", 80, 99, 90, key='detail_percentile')

    if municipality_detail:
        daily = get_arpa_daily_temperature(municipality_detail) if source == SOURCE_ARPA else get_daily_temperature(municipality_detail)
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
            "percentile trova più eventi locali di quella fissa: episodi che per "
            "quel comune sono davvero anomali, ma che i 35°C fissi ignorerebbero "
            "sempre."
        )

    st.subheader("Metodologia")
    st.markdown(
        "Alcune scelte fatte in questa pagina, spiegate:\n\n"
        "- **Perché in tutto il resto del sito si usa la soglia fissa (35°C) "
        "e non quella percentile?** Per avere un unico criterio semplice, "
        "uguale per ogni comune e facile da verificare, usato in modo "
        "coerente in tutte le pagine (i conteggi di ondate che vedi in home o "
        "nelle statistiche per comune sono sempre calcolati così). La "
        "definizione percentile qui sopra è un confronto illustrativo pensato "
        "per mostrare il limite di una soglia unica per tutti, **non "
        "sostituisce** i numeri ufficiali mostrati altrove nel sito.\n"
        "- **Perché la durata minima resta di 3 giorni anche con la soglia "
        "percentile?** Per confrontare le due definizioni a parità di "
        "condizioni — cambia solo \"quanto deve essere caldo\" un giorno per "
        "contare, non \"per quanti giorni di fila deve restare così\".\n"
        "- **Cosa mostra la heatmap \"calendario\"?** Prende tutte le ondate "
        "del periodo/comuni filtrati e le scompone giorno per giorno: per "
        "ogni combinazione (anno, giorno dell'anno) conta quanti comuni "
        "avevano un'ondata attiva proprio quel giorno. Più il colore è "
        "scuro, più comuni erano contemporaneamente in un'ondata quel "
        "giorno specifico — utile per vedere se, oltre a diventare più "
        "frequenti, le ondate iniziano anche a comparire più spesso fuori "
        "dai mesi centrali dell'estate."
    )
