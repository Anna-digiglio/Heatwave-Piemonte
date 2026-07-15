"""
05_download_dati.py - Export dei dati e dei risultati di analisi.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components import PROJECT_ROOT
from components.styling import inject_custom_css
from src.utils.config import config

st.set_page_config(page_title='Download Dati — Heatwave Piemonte', layout='wide')
inject_custom_css()
st.title("⬇️ Download Dati")
st.caption("Tutti i dati e i risultati mostrati in questo sito, scaricabili in formato CSV (apribile con Excel).")

FILES = [
    (
        "Temperature pulite (giornaliere, 2000-2025)",
        "Una riga per ogni giorno e comune: temperatura minima/media/massima, precipitazione. È la fonte di tutti i grafici del sito.",
        Path(config.get('paths.processed_data')) / 'temperature_clean.csv',
    ),
    (
        "Comuni piemontesi (ISTAT)",
        "Elenco e confini geografici dei 1180 comuni del Piemonte (non tutti hanno dati di temperatura, vedi Home).",
        Path(config.get('paths.external_data')) / 'municipalities.csv',
    ),
    (
        "Trend di riscaldamento per comune",
        "Risultato dei test Mann-Kendall e regressione lineare (pagina 'Analisi Temporale'): sale o scende la temperatura, e di quanto.",
        Path(config.get('paths.output')) / 'trend_analysis.csv',
    ),
    (
        "Statistiche ondate di calore per comune",
        "Numero, durata e intensità media delle ondate di calore per ciascun comune (pagina 'Ondate di Calore').",
        Path(config.get('paths.output')) / 'heatwave_stats_by_municipality.csv',
    ),
    (
        "Frequenza ondate di calore per anno",
        "Quante ondate di calore sono state rilevate ogni anno, sommando tutti i comuni.",
        Path(config.get('paths.output')) / 'heatwave_frequency_by_year.csv',
    ),
    (
        "Cluster climatici + Moran's I",
        "A quale zona climatica appartiene ogni comune (pagina 'Analisi Spaziale').",
        Path(config.get('paths.output')) / 'spatial_analysis.csv',
    ),
    (
        "Riepilogo scomposizione stagionale (STL)",
        "Quanto è cambiata la componente di trend (al netto della stagionalità) tra inizio e fine periodo, per comune.",
        Path(config.get('paths.output')) / 'seasonal_trend_summary.csv',
    ),
]

for label, description, path in FILES:
    full_path = (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path
    col_label, col_button = st.columns([3, 1])
    with col_label:
        st.write(f"**{label}**")
        st.caption(description)
    if full_path.exists():
        col_button.download_button(
            "Scarica CSV",
            data=full_path.read_bytes(),
            file_name=full_path.name,
            mime='text/csv',
            key=str(full_path),
        )
    else:
        col_button.caption("non ancora generato")
    st.divider()
