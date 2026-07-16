"""
download_extra_municipalities.py - Estende la copertura di temperature
reali oltre ai comuni già scaricati.

Motivazione: le analisi spaziali (Moran's I, clustering K-means, vedi
src/analysis/spatial_analysis.py) sono statisticamente deboli con poche
unità spaziali. Questo script seleziona comuni aggiuntivi con buona
distribuzione geografica per provincia (non i più vicini a quelli già
scaricati, ma quelli che massimizzano la copertura spaziale) e ne scarica
le temperature reali da Open-Meteo (stesso metodo/retry già usato).

Storia: eseguito una prima volta il 2026-07-15 per estendere da 8 a 44
comuni (TARGET_PER_PROVINCE sommava a 36). Tentativo il 2026-07-16 di
estendere a 300 comuni (256 aggiuntivi) fallito: dopo ~5h40 di download,
solo 37/256 comuni scaricati con successo e 123 falliti definitivamente
(rate limit di Open-Meteo sempre più severo dopo volume sostenuto) — e
siccome lo script salvava il CSV solo a fine esecuzione, l'interruzione ha
fatto perdere tutto il progresso. Ridimensionato lo stesso giorno a un
obiettivo più realistico: **100 comuni totali** (56 aggiuntivi), con due
fix strutturali per non ripetere l'errore:
1. **Salvataggio incrementale**: ogni comune scaricato con successo viene
   subito appeso al CSV di output, non solo alla fine — un'interruzione
   a metà non fa più perdere il lavoro già fatto.
2. **Pausa più lunga tra le richieste** (8s invece di 3s) per restare più
   lontani dalla soglia che ha innescato il rate limit progressivo.

Lo script resta idempotente rispetto a `already_downloaded_ids()`:
seleziona sempre e solo comuni non ancora scaricati (quindi è anche
sicuro da rilanciare dopo un'interruzione, ripartendo da dove il CSV
incrementale si era fermato).

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

# 56 comuni aggiuntivi (44 → 100 totali), allocati proporzionalmente al
# numero reale di comuni per provincia (Torino 312, Cuneo 247, Alessandria
# 187, Asti 117, Novara 87, Vercelli 82, Biella 74, VCO 74 - su 1180
# totali), meno quelli già scaricati nelle tornate precedenti.
TARGET_PER_PROVINCE = {
    'Torino': 15,
    'Cuneo': 12,
    'Alessandria': 9,
    'Asti': 5,
    'Novara': 4,
    'Vercelli': 3,
    'Biella': 4,
    'Verbano-Cusio-Ossola': 4,
}

REQUEST_SLEEP_SECONDS = 8


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


def download_all(
    selection: pd.DataFrame,
    output_path: Path,
    start_date: str = '2000-01-01',
    end_date: str = '2026-07-16',
) -> int:
    """
    Scarica le temperature per tutti i comuni selezionati, **appendendo
    ogni comune al CSV di output non appena scaricato** (non solo alla
    fine): se il processo viene interrotto a metà, i comuni già scritti
    restano salvati su disco invece di andare persi.

    Returns:
        int: numero di comuni scaricati con successo in questa esecuzione
    """
    downloader = WeatherDataDownloader()
    file_exists = output_path.exists()
    n_success = 0
    n_failed = 0

    for _, row in selection.iterrows():
        try:
            df = downloader.download_for_coordinates(row['name'], row['lat'], row['lon'], start_date, end_date)
            df['municipality_id'] = row['municipality_id']
            df['province_name'] = row['province_name']

            df.to_csv(output_path, mode='a', header=not file_exists, index=False)
            file_exists = True
            n_success += 1

            time.sleep(REQUEST_SLEEP_SECONDS)
        except Exception as e:
            logger.error(f"Errore download {row['name']}: {e}")
            n_failed += 1
            continue

    logger.info(f"✓ Download completato in questa esecuzione: {n_success} comuni riusciti, {n_failed} falliti")
    return n_success


def main():
    logger.info("=" * 70)
    logger.info("DOWNLOAD TEMPERATURE — COMUNI EXTRA (oltre a quelli già presenti)")
    logger.info("=" * 70)

    selection = select_extra_municipalities()
    logger.info(f"Totale comuni extra selezionati: {len(selection)}")

    output_path = Path(config.get('paths.raw_data')) / 'temperature_data_extra.csv'
    n_success = download_all(selection, output_path)

    logger.info(f"✓ Dati salvati incrementalmente in: {output_path} ({n_success} comuni aggiunti in questa esecuzione)")


if __name__ == '__main__':
    main()
