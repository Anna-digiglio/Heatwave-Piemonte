"""
02_analisi_temporale.py - Trend e scomposizione stagionale per comune.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components.queries import (
    get_daily_temperature,
    get_municipality_names_with_data,
    get_seasonal_decomposition,
    get_trend_analysis,
)

st.set_page_config(page_title='Analisi Temporale — Heatwave Piemonte', layout='wide')
st.title("📈 Analisi Temporale")
st.caption("La temperatura di ogni comune sta davvero cambiando nel tempo, o è solo variazione normale?")

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "Da un anno all'altro la temperatura media oscilla naturalmente "
        "(un'estate più fresca, un inverno più mite) — questo non significa "
        "che il clima stia cambiando. Per distinguere un **vero trend a "
        "lungo termine** dal semplice rumore anno-su-anno usiamo due metodi "
        "che si completano a vicenda:\n\n"
        "- **Test di Mann-Kendall**: risponde alla domanda *\"c'è un trend "
        "reale?\"* — sì/no, con un livello di confidenza statistico "
        "(non assume che i dati seguano una distribuzione particolare, il "
        "che lo rende affidabile anche con serie non perfettamente regolari).\n"
        "- **Regressione lineare**: se il trend c'è, risponde a "
        "*\"quanto è ripido?\"* — cioè quanti gradi in più (o in meno) per "
        "decennio.\n\n"
        "Il grafico **STL** più sotto scompone la serie giornaliera in tre "
        "pezzi separati: l'andamento di lungo periodo (trend), il ciclo "
        "estate/inverno che si ripete ogni anno (stagionalità), e ciò che "
        "resta — rumore giornaliero non spiegato dagli altri due (residuo)."
    )

names = get_municipality_names_with_data()
municipality = st.selectbox("Comune", names)

trend_df = get_trend_analysis()
row = trend_df[trend_df['municipality_name'] == municipality]

if not row.empty:
    row = row.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Trend (Mann-Kendall)", row['mk_trend'])
    col1.caption("'increasing' = temperatura in aumento nel periodo 2000-2025")
    col2.metric("Pendenza", f"{row['lr_slope_per_decade']:+.2f} °C/decade")
    col2.caption("Quanti gradi in più (o in meno) ogni 10 anni")
    col3.metric(
        "Significatività",
        f"p={row['lr_p_value']:.4f}",
        delta="significativo" if row['lr_p_value'] < 0.05 else "non significativo",
        delta_color="off",
    )
    col3.caption("p < 0.05 → il trend non è probabilmente casuale")
else:
    st.info("Nessun risultato di trend disponibile — esegui `python -m src.analysis.trend_analysis`.")

st.subheader(f"Serie giornaliera — {municipality}")
st.caption("Temperatura massima, media e minima registrata ogni giorno dal 2000 a oggi. Le punte verso l'alto in estate sono le potenziali ondate di calore (vedi pagina 'Ondate di Calore').")
daily = get_daily_temperature(municipality)

fig = go.Figure()
fig.add_trace(go.Scatter(x=daily['date'], y=daily['temp_max'], name='Max', line=dict(color='#e74c3c', width=1)))
fig.add_trace(go.Scatter(x=daily['date'], y=daily['temp_mean'], name='Media', line=dict(color='#f39c12', width=1)))
fig.add_trace(go.Scatter(x=daily['date'], y=daily['temp_min'], name='Min', line=dict(color='#3498db', width=1)))
fig.update_layout(height=350, margin=dict(t=10, b=10), yaxis_title='°C', legend=dict(orientation='h'))
st.plotly_chart(fig, width='stretch')

st.subheader("Scomposizione STL (trend / stagionalità / residuo)")
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
    st.caption(
        "Dall'alto in basso: **Trend** isola il segnale di riscaldamento a lungo termine "
        "(dovrebbe salire se il comune si sta scaldando); **Stagionalità** è il ciclo "
        "estate/inverno che si ripete identico ogni anno; **Residuo** è tutto ciò che "
        "resta — variazioni giornaliere impreviste (ondate di freddo/caldo anomale, rumore)."
    )
