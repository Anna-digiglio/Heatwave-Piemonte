"""
02_analisi_temporale.py - Serie storica, anomalie, stagionalità, trend.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats

from components.constants import (
    NATIONAL_GLOBAL_REFERENCE, SEASON_BY_MONTH, SEASON_COLORS, SEASON_ORDER, format_mk_trend,
)
from components.filters import render_sidebar_filters
from components.queries import (
    get_daily_temperature,
    get_kpi_annual,
    get_municipality_metadata,
    get_municipality_names_with_data,
    get_seasonal_decomposition,
    get_trend_analysis,
)
from components.styling import inject_custom_css

st.set_page_config(page_title='Analisi Temporale — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("📈 Analisi Temporale")
st.caption("La temperatura di ogni comune sta davvero cambiando nel tempo, o è solo variazione normale?")

year_start, year_end, provinces = render_sidebar_filters()

metadata = get_municipality_metadata()
names_in_provinces = sorted(metadata[metadata['province_name'].isin(provinces)]['municipality_name'])
names = names_in_provinces or get_municipality_names_with_data()
default_index = names.index('Torino') if 'Torino' in names else 0
municipality = st.selectbox("Comune", names, index=default_index)

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Da un anno all'altro la temperatura media oscilla naturalmente "
        "(un'estate più fresca, un inverno più mite) — questo non significa "
        "che il clima stia cambiando. Per distinguere un **vero trend a "
        "lungo termine** dal semplice rumore anno-su-anno usiamo:\n\n"
        "- **Test di Mann-Kendall**: risponde a *\"c'è un trend reale?\"* "
        "(sì/no, con un livello di confidenza statistico), calcolato una "
        "volta sull'intero periodo 2000-2025.\n"
        "- **Regressione lineare**: quantifica la pendenza in °C/decennio — "
        "qui ricalcolata **sul periodo selezionato nella sidebar**, così il "
        "grafico e la metrica in alto si aggiornano insieme se restringi "
        "l'intervallo di anni.\n\n"
        "Usa i **tab** sotto per passare dalla vista rapida (\"Panoramica\") "
        "al dettaglio statistico (Mann-Kendall, STL, metodologia)."
    )

annual = get_kpi_annual()
annual_m = annual[annual['municipality_name'] == municipality].sort_values('year')
annual_range = annual_m[(annual_m['year'] >= year_start) & (annual_m['year'] <= year_end)]

trend_df = get_trend_analysis()
trend_row = trend_df[trend_df['municipality_name'] == municipality]

# Regressione lineare ricalcolata sul periodo selezionato (non il CSV
# precalcolato, che copre sempre 2000-2025) — così il coefficiente in
# evidenza riflette davvero il filtro anni scelto dall'utente.
if len(annual_range) >= 2:
    slope_year, intercept, r_value, p_value, _ = stats.linregress(
        annual_range['year'], annual_range['temp_mean_annual']
    )
    slope_decade = slope_year * 10
else:
    slope_decade, p_value, r_value = None, None, None

baseline_years_available = int(annual_m['year'].min()) if not annual_m.empty else 2000
last_year = int(annual_m['year'].max()) if not annual_m.empty else 2025
last_year_temp = annual_m[annual_m['year'] == last_year]['temp_mean_annual']

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Pendenza (periodo selezionato)",
    f"{slope_decade:+.2f} °C/decade" if slope_decade is not None else "n/d",
)
col1.caption(f"Regressione lineare {year_start}-{year_end}")
col2.metric(
    "Significatività",
    f"p={p_value:.4f}" if p_value is not None else "n/d",
    delta="significativo" if (p_value is not None and p_value < 0.05) else "non significativo",
    delta_color="off",
)
col2.caption("p < 0.05 → il trend non è probabilmente casuale")
if not trend_row.empty:
    col3.metric("Trend Mann-Kendall (2000-2025)", format_mk_trend(trend_row.iloc[0]['mk_trend']))
    col3.caption("Test di riferimento sull'intero periodo, non filtrato")
else:
    col3.metric("Trend Mann-Kendall", "n/d")
col4.metric(
    f"Temp. media {last_year}",
    f"{last_year_temp.iloc[0]:.1f} °C" if not last_year_temp.empty else "n/d",
)
col4.caption("Ultimo anno disponibile per questo comune")

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

with tab_overview:
    st.subheader(f"Serie annuale con trend — {municipality}")
    st.caption(
        "Le tre linee sono la temperatura **massima, media e minima annuale**. "
        "La linea tratteggiata è la retta di regressione sulla temperatura media, "
        "calcolata solo sugli anni selezionati nella sidebar: più è inclinata, "
        "più veloce è il riscaldamento (o raffreddamento) in questo periodo."
    )
    if annual_range.empty:
        st.info("Nessun dato per il comune/periodo selezionato.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annual_range['year'], y=annual_range['temp_max_annual'], name='Max annuale', line=dict(color='#e74c3c')))
        fig.add_trace(go.Scatter(x=annual_range['year'], y=annual_range['temp_mean_annual'], name='Media annuale', line=dict(color='#f39c12')))
        fig.add_trace(go.Scatter(x=annual_range['year'], y=annual_range['temp_min_annual'], name='Min annuale', line=dict(color='#3498db')))
        if slope_decade is not None:
            trend_line = intercept + slope_year * annual_range['year']
            fig.add_trace(go.Scatter(
                x=annual_range['year'], y=trend_line, name='Trend (regressione)',
                line=dict(color='#2c3e50', dash='dash', width=2),
            ))
        fig.update_layout(height=380, margin=dict(t=10, b=10), yaxis_title='°C', legend=dict(orientation='h'))
        st.plotly_chart(fig, width='stretch')

    st.subheader("Anomalie termiche rispetto a una baseline")
    baseline_end = min(baseline_years_available + 9, last_year)
    baseline_mask = (annual_m['year'] >= baseline_years_available) & (annual_m['year'] <= baseline_end)
    baseline_mean = annual_m.loc[baseline_mask, 'temp_mean_annual'].mean() if baseline_mask.any() else None

    if baseline_mean is None:
        st.info("Dati insufficienti per calcolare una baseline per questo comune.")
    else:
        st.markdown(
            f"Quando si parla di cambiamento climatico, la domanda giusta non è "
            f"\"che temperatura ha fatto quest'anno\", ma \"quanto si discosta dal "
            f"passato\". Per rispondere serve un punto di riferimento fisso, "
            f"chiamato **baseline**: un periodo storico la cui temperatura media "
            f"viene usata come zero da cui misurare tutti gli scostamenti "
            f"successivi. In questo progetto la baseline è la **media "
            f"{baseline_years_available}-{baseline_end}**, il primo decennio "
            f"disponibile per questo comune — il punto più indietro nel tempo a "
            f"cui possiamo guardare con questi dati, ed è la stessa per tutti i "
            f"comuni analizzati, così i confronti tra zone diverse restano "
            f"coerenti.\n\n"
            f"Questo grafico non mostra quindi la temperatura assoluta di ogni "
            f"anno, ma la sua distanza da quella baseline. Le **barre rosse** "
            f"sopra lo zero indicano anni più caldi della media "
            f"{baseline_years_available}-{baseline_end}, le **barre blu** sotto "
            f"zero anni più freddi. Se osservando il grafico da sinistra a destra "
            f"le barre rosse diventano via via più frequenti e più alte, è il "
            f"segnale più diretto che il clima si sta scaldando rispetto a "
            f"{last_year - baseline_end} anni fa: non un singolo anno "
            f"caldo, ma una tendenza che si consolida nel tempo."
        )
        anomaly_df = annual_range.copy()
        anomaly_df['anomaly'] = anomaly_df['temp_mean_annual'] - baseline_mean
        anomaly_df['sign'] = np.where(anomaly_df['anomaly'] >= 0, 'Sopra baseline', 'Sotto baseline')
        fig_anom = px.bar(
            anomaly_df, x='year', y='anomaly', color='sign',
            color_discrete_map={'Sopra baseline': '#e74c3c', 'Sotto baseline': '#3498db'},
            labels={'year': 'Anno', 'anomaly': 'Anomalia (°C)', 'sign': ''},
        )
        fig_anom.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig_anom, width='stretch')
        st.caption(f"Baseline: media {baseline_years_available}-{baseline_end} = {baseline_mean:.1f} °C.")

    st.subheader("Quale stagione si sta scaldando di più?")
    st.caption(
        "Temperatura media per stagione, anno per anno. Se una linea sale più "
        "ripida delle altre, quella stagione si sta scaldando più velocemente "
        "delle altre — non è scontato che sia l'estate."
    )
    daily = get_daily_temperature(municipality)
    daily['year'] = daily['date'].dt.year
    daily['season'] = daily['date'].dt.month.map(SEASON_BY_MONTH)
    daily_range = daily[(daily['year'] >= year_start) & (daily['year'] <= year_end)]
    seasonal = daily_range.groupby(['year', 'season'])['temp_mean'].mean().reset_index()

    if seasonal.empty:
        st.info("Nessun dato giornaliero per il periodo selezionato.")
    else:
        fig_season = px.line(
            seasonal, x='year', y='temp_mean', color='season',
            category_orders={'season': SEASON_ORDER}, color_discrete_map=SEASON_COLORS,
            labels={'year': 'Anno', 'temp_mean': 'Temp. media (°C)', 'season': 'Stagione'},
        )
        fig_season.update_layout(height=320, margin=dict(t=10, b=10), legend=dict(orientation='h'))
        st.plotly_chart(fig_season, width='stretch')

        badge_cols = st.columns(4)
        for i, season in enumerate(SEASON_ORDER):
            s = seasonal[seasonal['season'] == season]
            if len(s) >= 2:
                slope_s, *_ = stats.linregress(s['year'], s['temp_mean'])
                badge_cols[i].metric(season, f"{slope_s * 10:+.2f} °C/decade")
            else:
                badge_cols[i].metric(season, "n/d")
        st.caption("Pendenza per stagione nel periodo selezionato (regressione lineare).")

    st.subheader("Variabilità per periodo di 5 anni")
    st.caption(
        "Non solo la media può cambiare: anche la **variabilità** (l'ampiezza "
        "delle oscillazioni giorno per giorno) può aumentare o diminuire nel "
        "tempo. Ogni box mostra la distribuzione delle temperature giornaliere "
        "in un quinquennio: box più alti/allungati = più variabilità, non solo "
        "più caldo."
    )
    if daily_range.empty:
        st.info("Nessun dato giornaliero per il periodo selezionato.")
    else:
        daily_range = daily_range.copy()
        daily_range['quinquennio'] = (daily_range['year'] // 5 * 5).astype(str) + '-' + (daily_range['year'] // 5 * 5 + 4).astype(str)
        fig_box = px.box(
            daily_range.sort_values('year'), x='quinquennio', y='temp_mean',
            labels={'quinquennio': 'Periodo', 'temp_mean': 'Temp. media giornaliera (°C)'},
        )
        fig_box.update_layout(height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig_box, width='stretch')

    st.subheader("Confronto con il contesto nazionale/globale")
    st.caption(
        "Valori di riferimento **pubblicati in letteratura scientifica** "
        "(IPCC AR6, rapporti ISPRA \"Gli indicatori del clima in Italia\") — "
        "non calcolati da questo progetto, non scaricati in tempo reale: "
        "servono solo a dare un'idea se il trend locale è in linea con quello "
        "più ampio o se se ne discosta."
    )
    ref_cols = st.columns(len(NATIONAL_GLOBAL_REFERENCE) + 1)
    ref_cols[0].metric(
        f"{municipality} (periodo selezionato)",
        f"{slope_decade:+.2f} °C/decade" if slope_decade is not None else "n/d",
    )
    for i, (label, value) in enumerate(NATIONAL_GLOBAL_REFERENCE.items(), start=1):
        ref_cols[i].metric(label, f"+{value:.2f} °C/decade")

with tab_detail:
    st.subheader("Test statistici sull'intero periodo (2000-2025)")
    if trend_row.empty:
        st.info("Nessun risultato di trend disponibile — esegui `python -m src.analysis.trend_analysis`.")
    else:
        row = trend_row.iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Mann-Kendall", format_mk_trend(row['mk_trend']))
        d2.metric("MK p-value", f"{row['mk_p_value']:.4f}")
        d3.metric("Sen's slope", f"{row['mk_sen_slope']:.4f} °C/anno")
        d4.metric("Regressione (°C/decade)", f"{row['lr_slope_per_decade']:+.2f}")
        st.caption(
            "Il **Sen's slope** è una stima robusta della pendenza (mediana delle "
            "pendenze tra tutte le coppie di punti), meno sensibile agli outlier "
            "della regressione lineare classica — qui usata solo come test di "
            "riferimento, non ricalcolata sul filtro anni."
        )

    st.subheader(f"Scomposizione STL (trend / stagionalità / residuo) — {municipality}")
    st.caption(
        "La **STL decomposition** scompone la serie giornaliera in tre pezzi: "
        "l'andamento di lungo periodo (**trend**), il ciclo estate/inverno che "
        "si ripete ogni anno (**stagionalità**), e ciò che resta — rumore "
        "giornaliero non spiegato dagli altri due (**residuo**)."
    )
    stl = get_seasonal_decomposition(municipality)
    if stl.empty:
        st.info("Nessuna decomposizione disponibile — esegui `python -m src.analysis.seasonal_analysis`.")
    else:
        stl_fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=('Trend', 'Stagionalità', 'Residuo'))
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['trend'], line=dict(color='#2c3e50')), row=1, col=1)
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['seasonal'], line=dict(color='#16a085', width=0.8)), row=2, col=1)
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['resid'], mode='markers', marker=dict(size=2, color='#95a5a6')), row=3, col=1)
        stl_fig.update_layout(height=550, showlegend=False, margin=dict(t=30, b=10))
        st.plotly_chart(stl_fig, width='stretch')

    st.subheader("Metodologia")
    st.markdown(
        "- **Stagioni**: definizione meteorologica standard (non astronomica) — "
        "Inverno = Dic/Gen/Feb, Primavera = Mar/Apr/Mag, Estate = Giu/Lug/Ago, "
        "Autunno = Set/Ott/Nov.\n"
        "- **Baseline anomalie**: fissa al primo decennio disponibile per il "
        "comune selezionato (non configurabile, per rendere i confronti "
        "coerenti tra un comune e l'altro).\n"
        "- **Regressione sul periodo selezionato**: ricalcolata ogni volta sugli "
        "anni scelti in sidebar, quindi diversa dal Mann-Kendall/Sen's slope qui "
        "sopra, che restano fissi sull'intero 2000-2025 come test di riferimento.\n"
        "- **Riferimenti nazionale/globale**: valori di letteratura (vedi tab "
        "Panoramica), non ricalcolati da questo progetto."
    )
