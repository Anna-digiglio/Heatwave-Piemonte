"""
download_extra_municipalities.py - Estende la copertura di temperature
reali oltre agli 8 comuni capoluogo.

Motivazione: le analisi spaziali (Moran's I, clustering K-means, vedi
src/analysis/spatial_analysis.py) sono statisticamente deboli con solo 8
unità spaziali. Questo script seleziona ~35 comuni aggiuntivi con buona
distribuzione geografica per provincia (non i più vicini ai capoluoghi già
scaricati, ma quelli che massimizzano la copertura spaziale) e ne scarica
le temperature reali da Open-Meteo (stesso metodo/retry degli 8 capoluoghi).

Usage:
    python -m src.data_acquisition.download_extra_municipalities
"""

from pathlib import Path

import numpy as np
import pandas as pd
import time

from src.data_acquisition.download_data import WeatherDataDownloader
from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

TARGET_PER_PROVINCE = {
    'Torino': 9,
    'Cuneo': 7,
    'Alessandria': 6,
    'Asti': 4,
    'Novara': 3,
    'Vercelli': 3,
    'Biella': 2,
    'Verbano-Cusio-Ossola': 2,
}


def load_all_municipalities() -> pd.DataFrame:
    """Carica id/nome/provincia/centroide di tutti i 1180 comuni."""
    query = """
        SELECT m.municipality_id, m.name, p.name AS province_name,
               ST_X(ST_Centroid(m.geometry)) AS lon,
               ST_Y(ST_Centroid(m.geometry)) AS lat
        FROM municipalities m
        JOIN provinces p ON m.province_id = p.province_id
    """
    rows = db_manager.execute_query(query)
    columns = ['municipality_id', 'name', 'province_name', 'lon', 'lat']
    return pd.DataFrame(rows, columns=columns)


def already_downloaded_ids() -> set:
    rows = db_manager.execute_query('SELECT DISTINCT municipality_id FROM temperature;')
    return {row[0] for row in rows}


def farthest_point_sample(candidates: pd.DataFrame, anchors: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Seleziona n comuni da `candidates` massimizzando la distanza minima
    dai punti già scelti (partendo dagli `anchors`, es. il capoluogo già
    scaricato) — così i comuni aggiunti coprono aree diverse della
    provincia invece di ammassarsi vicino a quelli già presenti.
    """
    chosen_coords = anchors[['lon', 'lat']].to_numpy()
    remaining = candidates.reset_index(drop=True)
    selected_rows = []

    for _ in range(min(n, len(remaining))):
        coords = remaining[['lon', 'lat']].to_numpy()
        # distanza minima di ciascun candidato da un qualunque punto già scelto
        dists = np.min(
            np.linalg.norm(coords[:, None, :] - chosen_coords[None, :, :], axis=2),
            axis=1,
        )
        best = np.argmax(dists)
        selected_rows.append(remaining.iloc[[best]])
        chosen_coords = np.vstack([chosen_coords, coords[best]])
        remaining = remaining.drop(remaining.index[best]).reset_index(drop=True)

    return pd.concat(selected_rows, ignore_index=True)


def select_extra_municipalities() -> pd.DataFrame:
    """Seleziona i comuni aggiuntivi da scaricare, per provincia."""
    all_muni = load_all_municipalities()
    downloaded = already_downloaded_ids()

    anchors_all = all_muni[all_muni['municipality_id'].isin(downloaded)]
    selections = []

    for province_name, target in TARGET_PER_PROVINCE.items():
        province_muni = all_muni[
            (all_muni['province_name'] == province_name)
            & (~all_muni['municipality_id'].isin(downloaded))
        ]
        anchors = anchors_all[anchors_all['province_name'] == province_name]
        if anchors.empty:
            # fallback: usa il centroide della provincia come anchor
            anchors = pd.DataFrame({'lon': [province_muni['lon'].mean()], 'lat': [province_muni['lat'].mean()]})

        picked = farthest_point_sample(province_muni, anchors, target)
        selections.append(picked)
        logger.info(f"{province_name}: selezionati {len(picked)} comuni extra")

    return pd.concat(selections, ignore_index=True)


def download_all(selection: pd.DataFrame, start_date: str = '2000-01-01', end_date: str = '2025-12-31') -> pd.DataFrame:
    """Scarica le temperature per tutti i comuni selezionati."""
    downloader = WeatherDataDownloader()
    all_data = []

    for _, row in selection.iterrows():
        try:
            df = downloader.download_for_coordinates(row['name'], row['lat'], row['lon'], start_date, end_date)
            df['municipality_id'] = row['municipality_id']
            df['province_name'] = row['province_name']
            all_data.append(df)
            time.sleep(3)
        except Exception as e:
            logger.error(f"Errore download {row['name']}: {e}")
            continue

    if not all_data:
        raise RuntimeError("Nessun dato scaricato")

    consolidated = pd.concat(all_data, ignore_index=True)
    logger.info(f"✓ Download completato: {len(consolidated)} righe, {selection.shape[0]} comuni")
    return consolidated


def main():
    logger.info("=" * 70)
    logger.info("DOWNLOAD TEMPERATURE — COMUNI EXTRA (oltre agli 8 capoluoghi)")
    logger.info("=" * 70)

    selection = select_extra_municipalities()
    logger.info(f"Totale comuni extra selezionati: {len(selection)}")

    raw_df = download_all(selection)

    output_path = Path(config.get('paths.raw_data')) / 'temperature_data_extra.csv'
    raw_df.to_csv(output_path, index=False)
    logger.info(f"✓ Dati salvati: {output_path}")


if __name__ == '__main__':
    main()
