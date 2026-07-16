"""
update_recent_data.py - Estende la serie storica fino a oggi per tutti i
comuni già presenti in `temperature`.

Motivazione: il download iniziale (8 capoluoghi) e le due estensioni
successive (a 44, poi a 300 comuni) si fermavano al 31/12/2025. Questo
script scarica solo il **delta** (dal 1° gennaio dell'anno corrente a
oggi) per tutti i comuni già scaricati, così la serie arriva fino
all'ultimo giorno realmente disponibile su Open-Meteo (di norma "oggi
stesso", verificato: nessun ritardo riscontrato per Torino il 2026-07-16).

Non ridownloada mai 2000-2025 (evita duplicati: `temperature` non ha un
vincolo di unicità su (municipality_id, date), quindi un doppio insert
sullo stesso periodo creerebbe righe duplicate silenziosamente).

Usage:
    python -m src.data_acquisition.update_recent_data
"""

from datetime import date
from pathlib import Path

import pandas as pd
import time

from src.data_acquisition.download_data import WeatherDataDownloader
from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_municipalities_with_data() -> pd.DataFrame:
    """Comuni già presenti in `temperature`, con centroide della geometria."""
    query = """
        SELECT DISTINCT m.municipality_id, m.name,
               ST_Y(ST_Centroid(m.geometry)) AS lat,
               ST_X(ST_Centroid(m.geometry)) AS lon
        FROM municipalities m
        JOIN temperature t ON t.municipality_id = m.municipality_id
        ORDER BY m.name
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_id', 'name', 'lat', 'lon']
    return pd.DataFrame(rows, columns=columns)


def latest_date_per_municipality() -> dict:
    """Ultima data già presente in `temperature` per ciascun comune."""
    rows = db_manager.execute_query(
        'SELECT municipality_id, MAX(date) FROM temperature GROUP BY municipality_id;'
    )
    return {row[0]: row[1] for row in rows}


def download_recent(municipalities: pd.DataFrame, latest_dates: dict, end_date: str) -> pd.DataFrame:
    """Scarica solo il delta (dal giorno dopo l'ultima data nota fino a end_date) per comune."""
    downloader = WeatherDataDownloader()
    all_data = []

    for _, row in municipalities.iterrows():
        last_known = latest_dates.get(row['municipality_id'])
        start_date = (last_known + pd.Timedelta(days=1)).strftime('%Y-%m-%d') if last_known else '2000-01-01'
        if start_date > end_date:
            continue
        try:
            df = downloader.download_for_coordinates(row['name'], row['lat'], row['lon'], start_date, end_date)
            if df.empty:
                continue
            df['municipality_id'] = row['municipality_id']
            all_data.append(df)
            time.sleep(3)
        except Exception as e:
            logger.error(f"Errore download {row['name']}: {e}")
            continue

    if not all_data:
        raise RuntimeError("Nessun dato scaricato")

    consolidated = pd.concat(all_data, ignore_index=True)
    logger.info(f"✓ Download delta completato: {len(consolidated)} righe, {len(all_data)} comuni")
    return consolidated


def main():
    logger.info("=" * 70)
    logger.info("AGGIORNAMENTO DATI RECENTI (fino ad oggi)")
    logger.info("=" * 70)

    today = date.today().strftime('%Y-%m-%d')
    municipalities = load_municipalities_with_data()
    latest_dates = latest_date_per_municipality()
    logger.info(f"{len(municipalities)} comuni con dati; aggiornamento fino al {today}")

    raw_df = download_recent(municipalities, latest_dates, today)

    output_path = Path(config.get('paths.raw_data')) / 'temperature_data_recent.csv'
    raw_df.to_csv(output_path, index=False)
    logger.info(f"✓ Dati salvati: {output_path}")


if __name__ == '__main__':
    main()
