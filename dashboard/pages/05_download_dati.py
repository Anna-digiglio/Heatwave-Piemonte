"""
05_download_dati.py - Export dei dati e dei risultati di analisi.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components import PROJECT_ROOT
from src.utils.config import config

st.set_page_config(page_title='Download Dati — Heatwave Piemonte', layout='wide')
st.title("⬇️ Download Dati")

FILES = [
    ("Temperature pulite (giornaliere, 2000-2025)", Path(config.get('paths.processed_data')) / 'temperature_clean.csv'),
    ("Comuni piemontesi (ISTAT)", Path(config.get('paths.external_data')) / 'municipalities.csv'),
    ("Trend di riscaldamento per comune", Path(config.get('paths.output')) / 'trend_analysis.csv'),
    ("Statistiche ondate di calore per comune", Path(config.get('paths.output')) / 'heatwave_stats_by_municipality.csv'),
    ("Frequenza ondate di calore per anno", Path(config.get('paths.output')) / 'heatwave_frequency_by_year.csv'),
    ("Cluster climatici + Moran's I", Path(config.get('paths.output')) / 'spatial_analysis.csv'),
    ("Riepilogo scomposizione stagionale (STL)", Path(config.get('paths.output')) / 'seasonal_trend_summary.csv'),
]

for label, path in FILES:
    full_path = (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path
    col_label, col_button = st.columns([3, 1])
    col_label.write(label)
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
