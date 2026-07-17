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

from components.charts import apply_chart_theme
from components.constants import (
    NATIONAL_GLOBAL_REFERENCE, SEASON_BY_MONTH, SEASON_COLORS, SEASON_ORDER, format_mk_trend,
)
from components.filters import render_year_range_filter
from components.queries import (
    get_daily_temperature,
    get_daily_temperature_aggregate,
    get_kpi_annual,
    get_municipality_names_with_data,
    get_seasonal_decomposition,
    get_seasonal_decomposition_aggregate,
    get_trend_analysis,
)
from components.styling import inject_custom_css
from src.analysis.trend_analysis import linear_trend, mann_kendall_trend

st.set_page_config(page_title='Analisi Temporale — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("📈 Analisi Temporale")
st.caption("La temperatura di ogni comune sta davvero cambiando nel tempo, o è solo variazione normale?")

names = get_municipality_names_with_data()

col_check, col_select = st.columns([1, 2])
with col_check:
    is_aggregate = st.checkbox(
        "🌍 Intero Piemonte",
        help=f"Calcola tutta la pagina sulla media dei {len(names)} comuni con dati, invece che su un singolo comune.",
    )
with col_select:
    default_index = names.index('Torino') if 'Torino' in names else 0
    municipality = st.selectbox("Comune", names, index=default_index, disabled=is_aggregate)

subject_label = f"Piemonte (media di {len(names)} comuni)" if is_aggregate else municipality

if is_aggregate:
    st.info(
        f"Stai guardando la **media aritmetica** (non pesata per popolazione o "
        f"superficie) dei {len(names)} comuni con dati reali — non una stima "
        "ufficiale della temperatura media del Piemonte, che richiederebbe "
        "pesare per area/popolazione e includere tutti i 1180 comuni."
    )

year_start, year_end = render_year_range_filter(key='temporale_year_range')
st.caption(
    "L'intervallo sopra determina il periodo mostrato nei grafici sotto. "
    "Il test di Mann-Kendall e la scomposizione STL restano invece calcolati "
    "sull'intero periodo disponibile, come riferimento fisso."
)

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Da un anno all'altro la temperatura media oscilla naturalmente "
        "(un'estate più fresca, un inverno più mite) — questo non significa "
        "che il clima stia cambiando. Per distinguere un **vero trend a "
        "lungo termine** dal semplice rumore anno-su-anno usiamo:\n\n"
        "- **Test di Mann-Kendall**: risponde a *\"c'è un trend reale?\"* "
        "(sì/no, con un livello di confidenza statistico), calcolato una "
        "volta sull'intero periodo disponibile.\n"
        "- **Regressione lineare**: quantifica la pendenza in °C/decennio — "
        "qui ricalcolata **sul periodo selezionato nella sidebar**, così il "
        "grafico e la metrica in alto si aggiornano insieme se restringi "
        "l'intervallo di anni.\n\n"
        "Usa i **tab** sotto per passare dalla vista rapida (\"Panoramica\") "
        "al dettaglio statistico (Mann-Kendall, STL, metodologia)."
    )

annual = get_kpi_annual()
if is_aggregate:
    annual_m = (
        annual[annual['municipality_name'].isin(names)]
        .groupby('year', as_index=False)
        .agg(
            temp_mean_annual=('temp_mean_annual', 'mean'),
            temp_max_annual=('temp_max_annual', 'mean'),
            temp_min_annual=('temp_min_annual', 'mean'),
        )
        .sort_values('year')
    )
else:
    annual_m = annual[annual['municipality_name'] == municipality].sort_values('year')
annual_range = annual_m[(annual_m['year'] >= year_start) & (annual_m['year'] <= year_end)]

# trend_info: risultato canonico di Mann-Kendall + regressione sull'intero
# periodo disponibile (non sul filtro anni). Per un singolo comune viene dal
# CSV precalcolato (`trend_analysis.csv`); per l'aggregato "Piemonte" non
# esiste un precalcolato, quindi si ricalcola al volo con le stesse funzioni
# pure usate da `src/analysis/trend_analysis.py`, per coerenza metodologica.
if is_aggregate:
    trend_info = {'municipality_name': subject_label}
    trend_info.update(mann_kendall_trend(annual_m['temp_mean_annual']))
    trend_info.update(linear_trend(annual_m['year'], annual_m['temp_mean_annual']))
    has_trend_info = True
else:
    trend_df = get_trend_analysis()
    trend_row = trend_df[trend_df['municipality_name'] == municipality]
    has_trend_info = not trend_row.empty
    trend_info = trend_row.iloc[0].to_dict() if has_trend_info else None

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
if has_trend_info:
    col3.metric("Trend Mann-Kendall (intero periodo)", format_mk_trend(trend_info['mk_trend']))
    col3.caption("Test di riferimento sull'intero periodo, non filtrato")
else:
    col3.metric("Trend Mann-Kendall", "n/d")
col4.metric(
    f"Temp. media {last_year}",
    f"{last_year_temp.iloc[0]:.1f} °C" if not last_year_temp.empty else "n/d",
)
col4.caption(f"Ultimo anno disponibile per {subject_label}")

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

with tab_overview:
    st.subheader(f"Serie annuale con trend — {subject_label}")
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
        st.plotly_chart(apply_chart_theme(fig), width='stretch')

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
        st.plotly_chart(apply_chart_theme(fig_anom), width='stretch')
        st.caption(f"Baseline: media {baseline_years_available}-{baseline_end} = {baseline_mean:.1f} °C.")

    st.subheader("Quale stagione si sta scaldando di più?")
    st.caption(
        "Temperatura media per stagione, anno per anno. Se una linea sale più "
        "ripida delle altre, quella stagione si sta scaldando più velocemente "
        "delle altre — non è scontato che sia l'estate."
    )
    daily = get_daily_temperature_aggregate(tuple(names)) if is_aggregate else get_daily_temperature(municipality)
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
        st.plotly_chart(apply_chart_theme(fig_season), width='stretch')

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
        st.plotly_chart(apply_chart_theme(fig_box), width='stretch')

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
        f"{subject_label} (periodo selezionato)",
        f"{slope_decade:+.2f} °C/decade" if slope_decade is not None else "n/d",
    )
    for i, (label, value) in enumerate(NATIONAL_GLOBAL_REFERENCE.items(), start=1):
        ref_cols[i].metric(label, f"+{value:.2f} °C/decade")

with tab_detail:
    st.subheader("Test statistici sull'intero periodo disponibile")
    if not has_trend_info:
        st.info("Nessun risultato di trend disponibile per questo comune.")
    else:
        row = trend_info
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Mann-Kendall", format_mk_trend(row['mk_trend']))
        d2.metric("MK p-value", f"{row['mk_p_value']:.4f}")
        d3.metric("Sen's slope", f"{row['mk_sen_slope']:.4f} °C/anno")
        d4.metric("Regressione (°C/decade)", f"{row['lr_slope_per_decade']:+.2f}")

        st.markdown(
            "**Cosa sono questi 4 numeri, in parole semplici:**\n\n"
            "- **Mann-Kendall** risponde a una sola domanda: *guardando tutti gli "
            "anni dal 2000 in poi, la temperatura sta seguendo una direzione "
            "chiara (sale o scende), oppure sale e scende a caso senza una vera "
            "tendenza?* Il test non guarda solo il primo e l'ultimo anno: "
            "confronta **ogni coppia possibile di anni** e conta quante volte "
            "l'anno più recente è stato più caldo di quello più vecchio rispetto "
            "a quante volte è successo il contrario. Se una delle due direzioni "
            "vince nettamente, c'è un trend reale; se il punteggio è quasi alla "
            "pari, probabilmente è solo variabilità naturale. Il vantaggio di "
            "questo metodo è che non si lascia ingannare da un singolo anno "
            "anomalo (un'estate eccezionalmente calda o fredda), perché guarda "
            "l'insieme di tutti i confronti, non solo alcuni punti.\n\n"
            "- **MK p-value** è la probabilità di aver visto per puro caso il "
            "risultato del test qui sopra, anche se in realtà **non ci fosse "
            "nessun trend reale**. È un numero tra 0 e 1: più è basso, più "
            "possiamo fidarci che il trend osservato sia vero e non un "
            "accidente statistico. La soglia comunemente usata è **0.05**: sotto "
            "quella soglia si considera il trend \"statisticamente "
            "significativo\", cioè abbastanza solido da non essere spiegato dal "
            "solo caso.\n\n"
            "- **Sen's slope** risponde a una domanda diversa: *non SE c'è un "
            "trend, ma DI QUANTO sale o scende ogni anno, in °C*. Per calcolarlo "
            "si prendono tutte le possibili coppie di anni, si calcola per "
            "ciascuna coppia \"quanto è cambiata la temperatura diviso quanti "
            "anni sono passati\", e poi si prende il valore **di mezzo** "
            "(la mediana) di tutti questi risultati. Usare il valore di mezzo "
            "invece della media rende questa stima molto più difficile da far "
            "\"sballare\" da un singolo anno estremo, che è esattamente il "
            "motivo per cui si affianca al test di Mann-Kendall invece di usare "
            "solo la regressione classica.\n\n"
            "- **Regressione (°C/decade)** è il modo più tradizionale e più "
            "diffuso di rispondere alla stessa domanda del punto sopra: si "
            "traccia la retta che meglio approssima tutti i punti della serie "
            "(la classica \"linea di tendenza\") e se ne legge l'inclinazione, "
            "convertita in gradi ogni 10 anni per essere più intuitiva. A "
            "differenza del Sen's slope, questo metodo tiene conto di ogni "
            "singolo valore nel calcolo, quindi un anno particolarmente estremo "
            "puó spostare un po' di più il risultato — resta comunque il numero "
            "più citato quando si parla di \"quanti gradi in più a decennio\", "
            "perché è lo stesso standard usato nella maggior parte dei report "
            "climatici.\n\n"
            "In sintesi: **Mann-Kendall + p-value** dicono se fidarsi del trend, "
            "**Sen's slope e regressione** dicono quanto è ripido — sono due "
            "stime della stessa pendenza calcolate in due modi diversi, ed è "
            "normale (e rassicurante) che siano simili tra loro."
            + (" Per l'aggregato \"Piemonte\" tutti e 4 questi numeri sono "
               "ricalcolati sulla media dei comuni filtrati con lo stesso "
               "metodo, non letti da un file già pronto." if is_aggregate else "")
        )

    st.subheader(f"Scomposizione STL (trend / stagionalità / residuo) — {subject_label}")
    st.markdown(
        "Una serie giornaliera di temperatura è \"rumorosa\": ogni giorno può "
        "essere più caldo o più freddo della media per mille motivi (un "
        "temporale, una perturbazione, un'ondata di aria fredda), e sopra a "
        "tutto questo si sovrappone il normale ciclo delle stagioni (fa più "
        "caldo d'estate, più freddo d'inverno, sempre, ogni anno). Se si guarda "
        "la temperatura grezza giorno per giorno è quasi impossibile capire se "
        "il clima si sta davvero scaldando, perché il segnale di riscaldamento "
        "(lento, su 26 anni) è nascosto sotto oscillazioni molto più grandi e "
        "veloci (stagionali e giornaliere). La scomposizione qui sotto separa "
        "questi tre livelli, uno per grafico:"
    )
    stl = get_seasonal_decomposition_aggregate(tuple(names)) if is_aggregate else get_seasonal_decomposition(municipality)
    if stl.empty:
        st.info("Nessuna decomposizione disponibile per questo comune.")
    else:
        stl_fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=('Trend', 'Stagionalità', 'Residuo'))
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['trend'], line=dict(color='#2c3e50')), row=1, col=1)
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['seasonal'], line=dict(color='#16a085', width=0.8)), row=2, col=1)
        stl_fig.add_trace(go.Scatter(x=stl['date'], y=stl['resid'], mode='markers', marker=dict(size=2, color='#95a5a6')), row=3, col=1)
        stl_fig.update_layout(height=550, showlegend=False, margin=dict(t=30, b=10))
        st.plotly_chart(apply_chart_theme(stl_fig), width='stretch')

        st.markdown(
            "- **Trend** (grafico in alto): è il segnale di lungo periodo, "
            "\"ripulito\" sia dalle stagioni sia dal rumore giornaliero — mostra "
            "solo la tendenza di fondo. Se questa linea sale andando da "
            "sinistra a destra, è la prova più diretta che questo comune si sta "
            "davvero scaldando nel tempo, indipendentemente da quale stagione è "
            "o da quanto è stato strano un singolo giorno.\n"
            "- **Stagionalità** (grafico centrale): è il ciclo che si ripete "
            "**identico** ogni anno — sale in estate, scende in inverno, sempre "
            "con la stessa forma. Rappresenta il normale susseguirsi delle "
            "stagioni, non un cambiamento nel tempo: infatti l'onda qui non "
            "diventa né più alta né più bassa andando avanti negli anni (a "
            "differenza del trend).\n"
            "- **Residuo** (grafico in basso): è tutto ciò che **non** è "
            "spiegato né dal trend né dalla stagionalità — i punti sparsi "
            "rappresentano giornate anomale rispetto a quello che ci si "
            "aspetterebbe in quel periodo dell'anno (un'ondata di calore fuori "
            "stagione, un crollo termico improvviso, possibili imprecisioni "
            "nella misura). Punti molto lontani dallo zero segnalano i giorni "
            "più \"fuori dal normale\" registrati."
        )

    st.subheader("Metodologia")
    st.markdown(
        "Alcune scelte fatte in questa pagina, spiegate:\n\n"
        "- **Perché due pendenze diverse (quella in alto e Sen's slope/"
        "regressione qui sotto)?** La pendenza mostrata nella tab Panoramica "
        "viene ricalcolata ogni volta che cambi l'intervallo di anni nella "
        "pagina, per farti vedere \"quanto si è scaldato solo nel periodo che "
        "hai scelto\". I 4 numeri di questa tab (Mann-Kendall, p-value, Sen's "
        "slope, regressione) restano invece **fissi sull'intero periodo "
        "disponibile**: servono come riferimento "
        "stabile, sempre uguale, per non confondere \"il trend di lungo periodo "
        "di questo comune\" con \"cosa è successo negli ultimi anni che hai "
        "scelto di guardare\".\n"
        "- **Perché le stagioni non coincidono con il calendario "
        "astronomico?** Uso la definizione **meteorologica**, standard in "
        "climatologia: Inverno = dicembre/gennaio/febbraio, Primavera = "
        "marzo/aprile/maggio, Estate = giugno/luglio/agosto, Autunno = "
        "settembre/ottobre/novembre. È più comoda di quella astronomica (che "
        "cambia data ogni anno e taglia i mesi a metà) perché raggruppa mesi "
        "interi, rendendo i confronti anno su anno coerenti.\n"
        "- **Perché la baseline delle anomalie è fissa e non modificabile?** "
        "È sempre la media del primo decennio di dati disponibile per il "
        "comune scelto (di solito 2000-2009): usare lo stesso tipo di "
        "riferimento per ogni comune rende i confronti tra zone diverse "
        "coerenti, invece di lasciare che ognuno scelga un periodo diverso e "
        "renda i risultati non paragonabili tra loro.\n"
        "- **Cosa sono i \"riferimenti nazionale/globale\" nella tab "
        "Panoramica?** Sono valori tipici citati nella letteratura "
        "scientifica (non calcolati da questo progetto, non aggiornati in "
        "tempo reale) messi lì solo per dare un termine di paragone: il "
        "trend di questo comune è più ripido, uguale o più lento di quello "
        "medio italiano o mondiale?"
    )
