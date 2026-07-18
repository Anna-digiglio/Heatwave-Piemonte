"""
queries.py - Funzioni di accesso dati per la dashboard.

Query al database (cache Streamlit per evitare round-trip ripetuti) e
lettura dei CSV prodotti da `src/analysis/` (vedi
wiki/pages/statistical-analysis.md).
"""

from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text

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
def get_daily_temperature_aggregate(municipality_names: tuple) -> pd.DataFrame:
    """
    Media giornaliera di temperatura sui comuni indicati - usata per
    l'opzione "Piemonte / media dei comuni filtrati" nella pagina Analisi
    Temporale. È una media aritmetica non pesata per popolazione/superficie
    dei soli comuni con dati reali passati in `municipality_names`, non una
    stima ufficiale della temperatura regionale (vedi
    wiki/pages/etl-pipeline.md per la granularità reale dei dati: 44 dei
    1180 comuni piemontesi).
    """
    query = text("""
        SELECT t.date,
               AVG(t.temp_mean)::float AS temp_mean,
               AVG(t.temp_max)::float AS temp_max,
               AVG(t.temp_min)::float AS temp_min,
               AVG(t.precipitation)::float AS precipitation
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        WHERE m.name IN :names
        GROUP BY t.date
        ORDER BY t.date
    """).bindparams(bindparam('names', expanding=True))
    with db_manager.engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'names': list(municipality_names)})
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
    per la mappa. Vedi wiki/pages/etl-pipeline.md per la nota di
    granularità (elenco comuni cresciuto nel tempo: 8 → 44 → 63 → 98 → 177).
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
def get_seasonal_decomposition_aggregate(municipality_names: tuple) -> pd.DataFrame:
    """
    STL decomposition calcolata al volo sulla media giornaliera dei comuni
    indicati (a differenza di `get_seasonal_decomposition`, che legge un
    CSV precalcolato per comune - qui non esiste un precalcolato per
    l'aggregato "Piemonte", quindi si ricalcola con la stessa funzione
    `decompose()` di `src/analysis/seasonal_analysis.py`).
    """
    from src.analysis.seasonal_analysis import decompose

    daily = get_daily_temperature_aggregate(municipality_names)
    if daily.empty:
        return pd.DataFrame()

    series = daily.set_index('date')['temp_mean'].asfreq('D')
    if series.isna().any():
        series = series.interpolate(method='linear')

    decomposed = decompose(series).reset_index()
    return decomposed


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


@st.cache_data(ttl=600)
def get_municipality_metadata() -> pd.DataFrame:
    """
    Metadati (provincia, elevazione, centroide) dei comuni con dati
    reali - usato per filtri, fasce altitudinali, mappe.
    """
    query = """
        SELECT DISTINCT m.name AS municipality_name, p.name AS province_name,
               m.elevation_m,
               ST_Y(ST_Centroid(m.geometry)) AS lat,
               ST_X(ST_Centroid(m.geometry)) AS lon
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    return pd.DataFrame(
        rows, columns=['municipality_name', 'province_name', 'elevation_m', 'lat', 'lon']
    )


@st.cache_data(ttl=600)
def get_province_geometries_wkt() -> pd.DataFrame:
    """
    Confine reale di ciascuna provincia, ottenuto aggregando via PostGIS
    (`ST_Union`) le geometrie di tutti i 1180 comuni ISTAT che appartengono
    a quella provincia (non solo i 44 con dati di temperatura) - usato per
    la mappa coropletica a livello provinciale.
    """
    query = """
        SELECT p.name AS province_name, ST_AsText(ST_Union(m.geometry)) AS geometry_wkt
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        GROUP BY p.name
    """
    rows = db_manager.execute_query(query)
    return pd.DataFrame(rows, columns=['province_name', 'geometry_wkt'])


@st.cache_data(ttl=600)
def get_land_cover_with_population() -> pd.DataFrame:
    """
    Uso del suolo (`municipality_land_cover`) e popolazione/densità per i
    comuni con dati di temperatura reali - join con `municipalities` per
    popolazione/area_km2 (entrambe popolate per tutti i 1180 comuni, non
    solo quelli con temperatura, vedi wiki/pages/data-sources.md), non solo
    le percentuali di uso del suolo.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               m.population, m.area_km2,
               l.pct_urban, l.pct_residential, l.pct_industrial_commercial,
               l.pct_transport, l.pct_urban_green, l.pct_agricultural,
               l.pct_forest_seminatural, l.pct_wetland, l.pct_water,
               l.dominant_class
        FROM municipality_land_cover l
        JOIN municipalities m ON m.municipality_id = l.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        WHERE l.municipality_id IN (SELECT DISTINCT municipality_id FROM temperature)
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_name', 'province_name', 'population', 'area_km2',
               'pct_urban', 'pct_residential', 'pct_industrial_commercial',
               'pct_transport', 'pct_urban_green', 'pct_agricultural',
               'pct_forest_seminatural', 'pct_wetland', 'pct_water', 'dominant_class']
    df = pd.DataFrame(rows, columns=columns)
    df['population'] = df['population'].astype(float)
    df['area_km2'] = df['area_km2'].astype(float)
    df['pop_density'] = df['population'] / df['area_km2']
    return df


@st.cache_data(ttl=600)
def get_land_cover_all() -> pd.DataFrame:
    """
    Uso del suolo e popolazione/densità per **tutti i 1180 comuni**
    piemontesi (non solo quelli con temperatura, a differenza di
    `get_land_cover_with_population`) - usato per le mappe di uso del
    suolo/popolazione, che hanno copertura completa indipendentemente
    dalla disponibilità di temperatura.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               m.population, m.area_km2, l.dominant_class,
               l.pct_urban, l.pct_industrial_commercial
        FROM municipality_land_cover l
        JOIN municipalities m ON m.municipality_id = l.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_name', 'province_name', 'population', 'area_km2',
               'dominant_class', 'pct_urban', 'pct_industrial_commercial']
    df = pd.DataFrame(rows, columns=columns)
    df['population'] = df['population'].astype(float)
    df['area_km2'] = df['area_km2'].astype(float)
    df['pop_density'] = df['population'] / df['area_km2']
    return df


@st.cache_data(ttl=600)
def get_all_municipality_geometries_wkt() -> pd.DataFrame:
    """
    Geometrie (come WKT) di **tutti i 1180 comuni** piemontesi, non solo
    quelli con dati di temperatura reali (a differenza di
    `get_municipality_geometries_wkt`) - usato per le mappe di uso del
    suolo/popolazione, che coprono l'intero territorio.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               ST_AsText(m.geometry) AS geometry_wkt
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    return pd.DataFrame(rows, columns=['municipality_name', 'province_name', 'geometry_wkt'])


@st.cache_data(ttl=600)
def get_ndvi_all() -> pd.DataFrame:
    """
    NDVI medio (`municipality_ndvi`) per tutti i 1180 comuni piemontesi -
    stesso pattern di `get_land_cover_all()`: copertura completa,
    indipendente dalla disponibilità di temperatura. Misura continua di
    densità della vegetazione, complementare alla classe di uso del suolo
    dominante di CORINE. Vedi wiki/pages/data-sources.md per la fonte
    (Copernicus Global Land Service NDVI 300m V3) e il periodo del
    composito usato.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               n.ndvi_mean, n.vegetation_class, n.pct_valid_pixels
        FROM municipality_ndvi n
        JOIN municipalities m ON m.municipality_id = n.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_name', 'province_name', 'ndvi_mean', 'vegetation_class', 'pct_valid_pixels']
    df = pd.DataFrame(rows, columns=columns)
    df['ndvi_mean'] = df['ndvi_mean'].astype(float)
    df['pct_valid_pixels'] = df['pct_valid_pixels'].astype(float)
    return df


@st.cache_data(ttl=600)
def get_kpi_annual_by_province() -> pd.DataFrame:
    """Serie annuale di KPI per provincia (vista kpi_annual_by_province)."""
    query = """
        SELECT p.name AS province_name, k.year, k.total_days,
               k.temp_mean_annual, k.temp_max_annual, k.temp_min_annual,
               k.days_gt_30c, k.days_gt_35c, k.days_gt_40c
        FROM kpi_annual_by_province k
        JOIN provinces p ON k.province_id = p.province_id
        ORDER BY p.name, k.year
    """
    rows = db_manager.execute_query(query)
    columns = ['province_name', 'year', 'total_days', 'temp_mean_annual',
               'temp_max_annual', 'temp_min_annual', 'days_gt_30c', 'days_gt_35c', 'days_gt_40c']
    return pd.DataFrame(rows, columns=columns)


