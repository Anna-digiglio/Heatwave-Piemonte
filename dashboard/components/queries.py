"""
queries.py - Funzioni di accesso dati per la dashboard.

Query al database (cache Streamlit per evitare round-trip ripetuti) e
lettura dei CSV prodotti da `src/analysis/` (vedi
wiki/pages/statistical-analysis.md).
"""

from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

from . import PROJECT_ROOT  # noqa: F401 (side effect: aggiunge la root al sys.path)
from src.utils.config import config
from src.utils.database import db_manager


@st.cache_data(ttl=600)
def get_overview_stats() -> dict:
    """Statistiche generali per la home page."""
    n_temperature = db_manager.execute_query('SELECT COUNT(*) FROM temperature;')[0][0]
    date_range = db_manager.execute_query('SELECT MIN(date), MAX(date) FROM temperature;')[0]
    n_municipalities = db_manager.execute_query('SELECT COUNT(*) FROM municipalities;')[0][0]
    n_municipalities_with_data = db_manager.execute_query(
        'SELECT COUNT(DISTINCT municipality_id) FROM temperature;'
    )[0][0]
    n_heatwaves = db_manager.execute_query('SELECT COUNT(*) FROM heatwave_events;')[0][0]
    return {
        'n_temperature_rows': n_temperature,
        'date_start': date_range[0],
        'date_end': date_range[1],
        'n_municipalities': n_municipalities,
        'n_municipalities_with_data': n_municipalities_with_data,
        'n_heatwaves': n_heatwaves,
    }


@st.cache_data(ttl=600)
def get_kpi_annual() -> pd.DataFrame:
    """Serie annuale di KPI per comune (vista kpi_annual_by_municipality)."""
    query = """
        SELECT m.name AS municipality_name, k.year, k.total_days,
               k.temp_mean_annual, k.temp_max_annual, k.temp_min_annual,
               k.days_gt_30c, k.days_gt_35c, k.days_gt_40c
        FROM kpi_annual_by_municipality k
        JOIN municipalities m ON k.municipality_id = m.municipality_id
        ORDER BY m.name, k.year
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_name', 'year', 'total_days', 'temp_mean_annual',
               'temp_max_annual', 'temp_min_annual', 'days_gt_30c', 'days_gt_35c', 'days_gt_40c']
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=600)
def get_daily_temperature(municipality_name: str) -> pd.DataFrame:
    """Serie giornaliera di temperatura per un comune."""
    query = text("""
        SELECT t.date, t.temp_mean, t.temp_max, t.temp_min, t.precipitation
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        WHERE m.name = :name
        ORDER BY t.date
    """)
    with db_manager.engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'name': municipality_name})
    df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data(ttl=600)
def get_heatwave_events() -> pd.DataFrame:
    """Tutte le ondate di calore rilevate, con nome comune/provincia."""
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               h.start_date, h.end_date, h.duration_days,
               h.max_temp, h.mean_temp, h.intensity_index
        FROM heatwave_events h
        JOIN municipalities m ON h.municipality_id = m.municipality_id
        JOIN provinces p ON h.province_id = p.province_id
        ORDER BY h.start_date
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_name', 'province_name', 'start_date', 'end_date',
               'duration_days', 'max_temp', 'mean_temp', 'intensity_index']
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=600)
def get_municipality_geometries_wkt() -> pd.DataFrame:
    """
    Geometrie (come WKT) dei comuni che hanno dati di temperatura reali,
    per la mappa. 44 comuni (8 capoluoghi + 36 extra), vedi
    wiki/pages/etl-pipeline.md per la nota di granularità.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               ST_AsText(m.geometry) AS geometry_wkt
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        WHERE m.municipality_id IN (SELECT DISTINCT municipality_id FROM temperature)
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    return pd.DataFrame(rows, columns=['municipality_name', 'province_name', 'geometry_wkt'])


def _output_path(filename: str) -> Path:
    return Path(config.get('paths.output')) / filename


@st.cache_data(ttl=600)
def get_trend_analysis() -> pd.DataFrame:
    """Risultati di src/analysis/trend_analysis.py (Mann-Kendall + regressione)."""
    path = _output_path('trend_analysis.csv')
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def get_heatwave_stats_by_municipality() -> pd.DataFrame:
    """Risultati di src/analysis/heatwave_stats.py."""
    path = _output_path('heatwave_stats_by_municipality.csv')
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def get_heatwave_frequency_by_year() -> pd.DataFrame:
    path = _output_path('heatwave_frequency_by_year.csv')
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def get_spatial_analysis() -> pd.DataFrame:
    """Risultati di src/analysis/spatial_analysis.py (cluster climatici)."""
    path = _output_path('spatial_analysis.csv')
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def get_morans_i_summary() -> pd.DataFrame:
    path = _output_path('morans_i_summary.csv')
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def get_seasonal_decomposition(municipality_name: str) -> pd.DataFrame:
    """Risultati di src/analysis/seasonal_analysis.py per un comune."""
    path = _output_path('seasonal_decomposition') / f'{municipality_name.lower()}_stl.csv'
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data(ttl=600)
def get_municipality_names_with_data() -> list:
    """Nomi dei comuni con dati di temperatura reali, ordinati alfabeticamente."""
    query = """
        SELECT DISTINCT m.name
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        ORDER BY m.name
    """
    return [row[0] for row in db_manager.execute_query(query)]
