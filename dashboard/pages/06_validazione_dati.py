"""
06_validazione_dati.py - Le temperature Open-Meteo confrontate con
osservazioni di stazione reali ARPA Piemonte (src/analysis/validate_arpa.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import plotly.express as px
import streamlit as st
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

from components.constants import MAP_TILES
from components.maps import render_gradient_legend, wkt_to_geojson
from components.queries import (
    get_arpa_event_comparison_summary,
    get_arpa_hot_day_bias,
    get_arpa_trend_comparison,
    get_arpa_validation,
    get_municipality_geometries_wkt,
    get_municipality_metadata,
)
from components.styling import inject_custom_css

st.set_page_config(page_title='Validazione Dati — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("🔍 Validazione dei Dati")
st.caption(
    "Le temperature usate in tutto questo sito vengono da Open-Meteo, un "
    "prodotto di rianalisi/modello — non da stazioni meteo reali. Quanto "
    "possiamo fidarci? Confronto diretto con le osservazioni reali di ARPA "
    "Piemonte."
)

with st.expander("ℹ️ Come si legge questa pagina", expanded=True):
    st.markdown(
        "- **ARPA Piemonte** gestisce la rete di stazioni meteo ufficiali "
        "della regione — quello che misura è un'**osservazione diretta**, "
        "non una stima. La confrontiamo con Open-Meteo (usato per il resto "
        "del sito) negli **51 comuni** dove esiste una stazione ARPA reale "
        "corrispondente, su oltre 20 anni di dati giornalieri.\n"
        "- **Bias** = differenza media (Open-Meteo − ARPA). Negativo = "
        "Open-Meteo sottostima la temperatura reale.\n"
        "- Il confronto più severo non è sulla temperatura media, ma su "
        "**quante ondate di calore reali Open-Meteo riesce a rilevare** — "
        "è la domanda che conta di più per un sito che parla di ondate di "
        "calore."
    )

validation = get_arpa_validation()
hot_bias = get_arpa_hot_day_bias()
trend_comparison = get_arpa_trend_comparison()
event_summary = get_arpa_event_comparison_summary()

if validation.empty:
    st.warning(
        "Dati di validazione non ancora generati. Esegui "
        "`python -m src.analysis.validate_arpa` per produrli."
    )
    st.stop()

# --- KPI di sintesi ---------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Comuni con stazione ARPA", len(validation))
k1.caption("Su 177 comuni con dati Open-Meteo")
k2.metric("Bias medio (temp. massima)", f"{validation['temp_max_bias'].mean():+.2f} °C")
k2.caption("Open-Meteo − ARPA, media sui comuni")
k3.metric("Correlazione media", f"{validation['temp_max_r'].mean():.3f}")
k3.caption("Pearson r, giorno per giorno")
if event_summary:
    k4.metric("Ondate di calore rilevate", f"{event_summary['recall']:.0%}")
    k4.caption(f"{int(event_summary['n_om_events'])} rilevate su {int(event_summary['n_arpa_events'])} reali (ARPA)")

if event_summary:
    st.error(
        "**Il dato più importante di questa pagina**: sui comuni con "
        f"riscontro reale, Open-Meteo rileva solo il "
        f"**{event_summary['recall']:.0%} delle ondate di calore "
        f"effettivamente accadute** ({int(event_summary['n_arpa_events'])} "
        f"reali secondo ARPA, contro {int(event_summary['n_om_events'])} "
        "rilevate da Open-Meteo). Le ondate di calore contate in tutto "
        "questo sito sono quindi quasi certamente un **sottoconteggio** del "
        "fenomeno reale — non un numero prudente."
    )

tab_overview, tab_detail = st.tabs(["📊 Panoramica", "🔬 Dettaglio tecnico / metodologia"])

with tab_overview:
    st.subheader("Bias per comune")
    st.caption(
        "Ogni comune è colorato in base al bias sulla temperatura massima "
        "(Open-Meteo − ARPA). Blu = Open-Meteo sottostima la temperatura "
        "reale (la maggioranza dei casi); rosso = la sovrastima."
    )
    geo_df = get_municipality_geometries_wkt()
    bias_points = validation.merge(geo_df, on='municipality_name')

    if bias_points.empty:
        st.info("Nessun comune con geometria disponibile per la mappa.")
    else:
        max_abs_bias = bias_points['temp_max_bias'].abs().max() or 1
        cmap_bias = LinearColormap(['#3498db', '#f7f7f7', '#e74c3c'], vmin=-max_abs_bias, vmax=max_abs_bias)
        m = folium.Map(location=[45.0, 8.0], zoom_start=8, tiles=MAP_TILES)
        for _, row in bias_points.iterrows():
            color = cmap_bias(row['temp_max_bias'])
            folium.GeoJson(
                wkt_to_geojson(row['geometry_wkt']),
                tooltip=(
                    f"{row['municipality_name']}: bias {row['temp_max_bias']:+.2f}°C, "
                    f"r={row['temp_max_r']:.3f} (stazione: {row['station_name']})"
                ),
                style_function=lambda _, c=color: {'fillColor': c, 'color': '#555', 'weight': 1, 'fillOpacity': 0.85},
            ).add_to(m)
        st_folium(m, width=None, height=420, returned_objects=[], key='map_arpa_bias')
        render_gradient_legend(
            cmap_bias, -max_abs_bias, max_abs_bias,
            labels=["Sottostima forte", "Sottostima lieve", "Accurato", "Sovrastima lieve", "Sovrastima forte"],
            unit="°C", title="Legenda — bias Open-Meteo vs ARPA", signed=True,
        )

    metadata = get_municipality_metadata()
    validation_elev = validation.merge(metadata[['municipality_name', 'elevation_m']], on='municipality_name', how='left')

    col_scatter1, col_scatter2 = st.columns(2)
    with col_scatter1:
        st.subheader("Bias vs elevazione")
        st.caption(
            "Più alto il comune, più Open-Meteo tende a sottostimare le "
            "massime reali (r=-0.35, p=0.012) — coerente con un prodotto di "
            "rianalisi che media una cella di griglia, non un punto, in "
            "rilievo alpino complesso."
        )
        fig_elev = px.scatter(
            validation_elev, x='elevation_m', y='temp_max_bias', hover_name='municipality_name',
            labels={'temp_max_bias': 'Bias temp. massima (°C)', 'elevation_m': 'Elevazione comune (m)'},
            trendline='ols',
        )
        fig_elev.add_hline(y=0, line_dash='dash', line_color='gray')
        st.plotly_chart(fig_elev, width='stretch')
    with col_scatter2:
        st.subheader("Distribuzione del bias sui 51 comuni")
        st.caption("La maggior parte dei comuni ha bias negativo (Open-Meteo sottostima).")
        fig_hist = px.histogram(
            validation, x='temp_max_bias', nbins=20,
            labels={'temp_max_bias': 'Bias temp. massima (°C)'},
        )
        fig_hist.add_vline(x=0, line_dash='dash', line_color='gray')
        fig_hist.add_vline(x=validation['temp_max_bias'].mean(), line_color='#e74c3c',
                            annotation_text='media')
        st.plotly_chart(fig_hist, width='stretch')

    st.subheader("Tabella completa per comune")
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

with tab_detail:
    st.subheader("Bias sui giorni davvero caldi")
    st.caption(
        "Il bias medio sopra è calcolato su tutti i giorni dell'anno — qui "
        "ristretto ai giorni con temperatura ARPA (verità di terra) sopra "
        "soglia. Il bias resta simile, ma la correlazione crolla: Open-Meteo "
        "perde la capacità di distinguere quali giorni estremi lo sono "
        "davvero di più."
    )
    if not hot_bias.empty:
        st.dataframe(
            hot_bias.rename(columns={
                'condition': 'Condizione', 'n_days': 'Giorni', 'bias': 'Bias (°C)',
                'mae': 'MAE (°C)', 'rmse': 'RMSE (°C)', 'r': 'Correlazione (r)', 'r_p_value': 'p-value',
            }),
            width='stretch', hide_index=True,
        )

    st.subheader("Confronto a livello di evento")
    st.caption(
        "Stessa logica di identificazione delle ondate di calore usata in "
        "tutto il sito (≥3 giorni consecutivi sopra 35°C), applicata ai dati "
        "ARPA e confrontata con le ondate già rilevate da Open-Meteo negli "
        "stessi comuni, per sovrapposizione temporale."
    )
    if event_summary:
        ec1, ec2, ec3, ec4 = st.columns(4)
        ec1.metric("Ondate ARPA (reali)", int(event_summary['n_arpa_events']))
        ec2.metric("Ondate Open-Meteo", int(event_summary['n_om_events']))
        ec3.metric("Precision", f"{event_summary['precision']:.1%}")
        ec3.caption("Delle ondate Open-Meteo, quante sono confermate da ARPA")
        ec4.metric("Recall", f"{event_summary['recall']:.1%}")
        ec4.caption("Delle ondate reali (ARPA), quante Open-Meteo cattura")

    st.subheader("Il trend di riscaldamento regge?")
    st.caption(
        "A differenza del conteggio delle ondate, il trend di riscaldamento "
        "(Mann-Kendall + regressione lineare) è risultato robusto alla fonte "
        "dati: il segno della pendenza concorda tra ARPA e Open-Meteo "
        "nell'88% dei comuni, e nessun comune mostra trend opposti "
        "*entrambi* statisticamente significativi."
    )
    if not trend_comparison.empty:
        both = trend_comparison.dropna(subset=['om_slope_per_decade'])
        display_cols_t = [c for c in [
            'municipality_name', 'arpa_slope_per_decade', 'arpa_mk_p_value',
            'om_slope_per_decade', 'om_mk_p_value',
        ] if c in both.columns]
        st.dataframe(
            both[display_cols_t].rename(columns={
                'municipality_name': 'Comune', 'arpa_slope_per_decade': 'Pendenza ARPA (°C/decade)',
                'arpa_mk_p_value': 'p-value ARPA', 'om_slope_per_decade': 'Pendenza Open-Meteo (°C/decade)',
                'om_mk_p_value': 'p-value Open-Meteo',
            }),
            width='stretch', hide_index=True,
        )

    st.subheader("Metodologia")
    st.markdown(
        "- **Fonte ARPA**: `utility.arpa.piemonte.it/meteoidro/`, API REST "
        "pubblica di ARPA Piemonte (non un servizio Open-Meteo) — vedi "
        "`wiki/pages/data-sources.md` per il dettaglio tecnico completo.\n"
        "- **Matching comune↔stazione**: per ciascun comune con più stazioni "
        "attive (tipico nei comuni alpini estesi), scelta quella con quota "
        "più vicina all'elevazione del comune.\n"
        "- **Bias/MAE/RMSE/correlazione**: calcolati su tutte le coppie "
        "(comune, data) disponibili in entrambe le fonti, 2000–oggi.\n"
        "- **Caveat**: la stazione scelta non è necessariamente "
        "rappresentativa dell'intero territorio comunale, specie nei comuni "
        "alpini estesi dove può essere un rifugio a quota molto diversa dal "
        "fondovalle abitato."
    )
