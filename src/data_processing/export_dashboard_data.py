"""
export_dashboard_data.py - Esporta uno snapshot dei dati per la dashboard.

Legge da Postgres (Open-Meteo + ARPA) e dai CSV gia' prodotti da
`src/analysis/*.py` in `output/`, e scrive tutto come Parquet in
`data/dashboard_export/` - l'unica cartella dati letta da
`dashboard/components/queries.py`, tracciata in Git (a differenza di
`output/` e dei dati grezzi, esclusi da `.gitignore`). Da rilanciare
manualmente dopo ogni sessione di aggiornamento dati (nuovi comuni, nuove
analisi), prima di fare commit/push per aggiornare la dashboard pubblicata.

Uso:
    python -m src.data_processing.export_dashboard_data
"""

import json
from pathlib import Path

import pandas as pd

from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

EXPORT_DIR = Path(config.get('paths.dashboard_export'))
OUTPUT_DIR = Path(config.get('paths.output'))

CSV_TO_COPY = [
    'trend_analysis.csv',
    'heatwave_stats_by_municipality.csv',
    'arpa_validation.csv',
    'arpa_hot_day_bias.csv',
    'arpa_trend_comparison.csv',
    'arpa_event_comparison_summary.csv',
    'heatwave_frequency_by_year.csv',
    'spatial_analysis.csv',
    'morans_i_summary.csv',
]


def _query_df(query: str, columns: list) -> pd.DataFrame:
    rows = db_manager.execute_query(query)
    return pd.DataFrame(rows, columns=columns)


def export_overview_stats() -> None:
    """Conteggi generali Open-Meteo + ARPA (equivalente di get_overview_stats + get_arpa_overview_stats)."""
    n_temperature = db_manager.execute_query('SELECT COUNT(*) FROM temperature;')[0][0]
    date_range = db_manager.execute_query('SELECT MIN(date), MAX(date) FROM temperature;')[0]
    n_municipalities = db_manager.execute_query('SELECT COUNT(*) FROM municipalities;')[0][0]
    n_municipalities_with_data = db_manager.execute_query(
        'SELECT COUNT(DISTINCT municipality_id) FROM temperature;'
    )[0][0]
    n_heatwaves = db_manager.execute_query('SELECT COUNT(*) FROM heatwave_events;')[0][0]
    n_arpa_rows = db_manager.execute_query('SELECT COUNT(*) FROM arpa_temperature;')[0][0]
    n_arpa_municipalities = db_manager.execute_query(
        'SELECT COUNT(DISTINCT municipality_id) FROM arpa_temperature;'
    )[0][0]

    stats = {
        'n_temperature_rows': n_temperature,
        'date_start': str(date_range[0]),
        'date_end': str(date_range[1]),
        'n_municipalities': n_municipalities,
        'n_municipalities_with_data': n_municipalities_with_data,
        'n_heatwaves': n_heatwaves,
        'n_arpa_rows': n_arpa_rows,
        'n_arpa_municipalities': n_arpa_municipalities,
    }
    with open(EXPORT_DIR / 'overview_stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"overview_stats.json: {stats}")


def export_temperature_daily_all() -> None:
    """Serie giornaliera Open-Meteo completa (equivalente di get_daily_temperature/_aggregate)."""
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               t.date, t.temp_mean, t.temp_max, t.temp_min, t.precipitation
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name, t.date
    """
    columns = ['municipality_name', 'province_name', 'date', 'temp_mean',
               'temp_max', 'temp_min', 'precipitation']
    df = _query_df(query, columns)
    df['date'] = pd.to_datetime(df['date'])
    df.to_parquet(EXPORT_DIR / 'temperature_daily_all.parquet', index=False)
    logger.info(f"temperature_daily_all.parquet: {len(df)} righe")


def export_arpa_temperature_daily_all() -> None:
    """Serie giornaliera ARPA completa (equivalente di get_arpa_daily_temperature/_multi)."""
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               a.date, a.temp_mean, a.temp_max, a.temp_min
        FROM arpa_temperature a
        JOIN municipalities m ON a.municipality_id = m.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name, a.date
    """
    columns = ['municipality_name', 'province_name', 'date', 'temp_mean', 'temp_max', 'temp_min']
    df = _query_df(query, columns)
    df['date'] = pd.to_datetime(df['date'])
    df.to_parquet(EXPORT_DIR / 'arpa_temperature_daily_all.parquet', index=False)
    logger.info(f"arpa_temperature_daily_all.parquet: {len(df)} righe")


def export_kpi_annual() -> None:
    query = """
        SELECT m.name AS municipality_name, k.year, k.total_days,
               k.temp_mean_annual, k.temp_max_annual, k.temp_min_annual,
               k.days_gt_30c, k.days_gt_35c, k.days_gt_40c
        FROM kpi_annual_by_municipality k
        JOIN municipalities m ON k.municipality_id = m.municipality_id
        ORDER BY m.name, k.year
    """
    columns = ['municipality_name', 'year', 'total_days', 'temp_mean_annual',
               'temp_max_annual', 'temp_min_annual', 'days_gt_30c', 'days_gt_35c', 'days_gt_40c']
    df = _query_df(query, columns)
    df.to_parquet(EXPORT_DIR / 'kpi_annual.parquet', index=False)


def export_kpi_annual_by_province() -> None:
    query = """
        SELECT p.name AS province_name, k.year, k.total_days,
               k.temp_mean_annual, k.temp_max_annual, k.temp_min_annual,
               k.days_gt_30c, k.days_gt_35c, k.days_gt_40c
        FROM kpi_annual_by_province k
        JOIN provinces p ON k.province_id = p.province_id
        ORDER BY p.name, k.year
    """
    columns = ['province_name', 'year', 'total_days', 'temp_mean_annual',
               'temp_max_annual', 'temp_min_annual', 'days_gt_30c', 'days_gt_35c', 'days_gt_40c']
    df = _query_df(query, columns)
    df.to_parquet(EXPORT_DIR / 'kpi_annual_by_province.parquet', index=False)


def export_heatwave_events() -> None:
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               h.start_date, h.end_date, h.duration_days,
               h.max_temp, h.mean_temp, h.intensity_index
        FROM heatwave_events h
        JOIN municipalities m ON h.municipality_id = m.municipality_id
        JOIN provinces p ON h.province_id = p.province_id
        ORDER BY h.start_date
    """
    columns = ['municipality_name', 'province_name', 'start_date', 'end_date',
               'duration_days', 'max_temp', 'mean_temp', 'intensity_index']
    df = _query_df(query, columns)
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    df.to_parquet(EXPORT_DIR / 'heatwave_events.parquet', index=False)


def export_municipality_metadata_all() -> None:
    """
    Provincia/elevazione/centroide per tutti i 1180 comuni - unifica in un
    solo file get_municipality_metadata() e get_arpa_municipality_metadata(),
    che in queries.py diventano lo stesso Parquet filtrato per nome comune.
    """
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               m.elevation_m,
               ST_Y(ST_Centroid(m.geometry)) AS lat,
               ST_X(ST_Centroid(m.geometry)) AS lon
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    columns = ['municipality_name', 'province_name', 'elevation_m', 'lat', 'lon']
    df = _query_df(query, columns)
    df.to_parquet(EXPORT_DIR / 'municipality_metadata_all.parquet', index=False)


def export_all_municipality_geometries() -> None:
    """Geometrie WKT di tutti i 1180 comuni - base comune per le mappe di ogni fonte."""
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               ST_AsText(m.geometry) AS geometry_wkt
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    columns = ['municipality_name', 'province_name', 'geometry_wkt']
    df = _query_df(query, columns)
    df.to_parquet(EXPORT_DIR / 'all_municipality_geometries.parquet', index=False)


def export_province_geometries() -> None:
    query = """
        SELECT p.name AS province_name, ST_AsText(ST_Union(m.geometry)) AS geometry_wkt
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
        GROUP BY p.name
    """
    columns = ['province_name', 'geometry_wkt']
    df = _query_df(query, columns)
    df.to_parquet(EXPORT_DIR / 'province_geometries.parquet', index=False)


def export_land_cover_with_population() -> None:
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
    columns = ['municipality_name', 'province_name', 'population', 'area_km2',
               'pct_urban', 'pct_residential', 'pct_industrial_commercial',
               'pct_transport', 'pct_urban_green', 'pct_agricultural',
               'pct_forest_seminatural', 'pct_wetland', 'pct_water', 'dominant_class']
    df = _query_df(query, columns)
    df['population'] = df['population'].astype(float)
    df['area_km2'] = df['area_km2'].astype(float)
    df.to_parquet(EXPORT_DIR / 'land_cover_with_population.parquet', index=False)


def export_land_cover_all() -> None:
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               m.population, m.area_km2, l.dominant_class,
               l.pct_urban, l.pct_industrial_commercial
        FROM municipality_land_cover l
        JOIN municipalities m ON m.municipality_id = l.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    columns = ['municipality_name', 'province_name', 'population', 'area_km2',
               'dominant_class', 'pct_urban', 'pct_industrial_commercial']
    df = _query_df(query, columns)
    df['population'] = df['population'].astype(float)
    df['area_km2'] = df['area_km2'].astype(float)
    df.to_parquet(EXPORT_DIR / 'land_cover_all.parquet', index=False)


def export_ndvi_all() -> None:
    query = """
        SELECT m.name AS municipality_name, p.name AS province_name,
               n.ndvi_mean, n.vegetation_class, n.pct_valid_pixels
        FROM municipality_ndvi n
        JOIN municipalities m ON m.municipality_id = n.municipality_id
        JOIN provinces p ON m.province_id = p.province_id
        ORDER BY m.name
    """
    columns = ['municipality_name', 'province_name', 'ndvi_mean', 'vegetation_class', 'pct_valid_pixels']
    df = _query_df(query, columns)
    df['ndvi_mean'] = df['ndvi_mean'].astype(float)
    df['pct_valid_pixels'] = df['pct_valid_pixels'].astype(float)
    df.to_parquet(EXPORT_DIR / 'ndvi_all.parquet', index=False)


def export_seasonal_decomposition_all() -> None:
    """
    Consolida i CSV per-comune di output/seasonal_decomposition/ (uno per
    comune, nome file in minuscolo) in un solo Parquet con colonna
    municipality_name - molto piu' leggero di centinaia di file separati
    (121 MB in CSV a 177 comuni) grazie alla compressione colonnare.
    """
    src_dir = OUTPUT_DIR / 'seasonal_decomposition'
    if not src_dir.exists():
        logger.warning(f"{src_dir} non trovata, salto seasonal_decomposition_all")
        return

    # I nomi file sono sempre in minuscolo (vedi get_seasonal_decomposition in
    # queries.py: f'{municipality_name.lower()}_stl.csv') - risaliamo al nome
    # comune col case originale tramite i metadati dei comuni con temperatura.
    names = db_manager.execute_query(
        "SELECT DISTINCT m.name FROM temperature t "
        "JOIN municipalities m ON t.municipality_id = m.municipality_id"
    )
    name_by_lower = {row[0].lower(): row[0] for row in names}

    frames = []
    for csv_path in sorted(src_dir.glob('*_stl.csv')):
        stem = csv_path.stem[: -len('_stl')]
        municipality_name = name_by_lower.get(stem, stem)
        df = pd.read_csv(csv_path)
        df['municipality_name'] = municipality_name
        frames.append(df)

    if not frames:
        logger.warning("Nessun CSV di scomposizione stagionale trovato")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date'])
    # float32 + gzip invece del default (float64 + snappy): a 599 comuni il
    # file superava i 100MB del limite GitHub (154MB) - scoperto il
    # 2026-07-23 quando il push e' stato respinto. float32 e' piu' che
    # sufficiente per temperature in gradi (nessuna perdita di precisione
    # rilevante), gzip comprime meglio di snappy per questo tipo di dati
    # (83MB contro 93MB con solo float32).
    for col in ['observed', 'trend', 'seasonal', 'resid']:
        combined[col] = combined[col].astype('float32')
    combined.to_parquet(
        EXPORT_DIR / 'seasonal_decomposition_all.parquet', index=False, compression='gzip'
    )
    logger.info(f"seasonal_decomposition_all.parquet: {len(combined)} righe, {len(frames)} comuni")


def export_output_csvs() -> None:
    """Copia 1:1 (solo cambio formato/percorso) delle altre CSV di output/ gia' usate dalla dashboard."""
    for filename in CSV_TO_COPY:
        csv_path = OUTPUT_DIR / filename
        if not csv_path.exists():
            logger.warning(f"{csv_path} non trovato, salto")
            continue
        df = pd.read_csv(csv_path)
        parquet_name = Path(filename).stem + '.parquet'
        df.to_parquet(EXPORT_DIR / parquet_name, index=False)
        logger.info(f"{parquet_name}: {len(df)} righe")


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Export dashboard verso {EXPORT_DIR}")

    export_overview_stats()
    export_temperature_daily_all()
    export_arpa_temperature_daily_all()
    export_kpi_annual()
    export_kpi_annual_by_province()
    export_heatwave_events()
    export_municipality_metadata_all()
    export_all_municipality_geometries()
    export_province_geometries()
    export_land_cover_with_population()
    export_land_cover_all()
    export_ndvi_all()
    export_seasonal_decomposition_all()
    export_output_csvs()

    logger.info("Export completato")


if __name__ == '__main__':
    main()
