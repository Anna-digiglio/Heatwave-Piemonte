"""
download_arpa.py - Scarica temperature giornaliere osservate da ARPA Piemonte
per la validazione delle stime Open-Meteo (dati di rianalisi/modello, non
osservazioni dirette) gia' caricate in `temperature`.

Contesto: fase 1 del piano paper (wiki/pages/paper-scientifico.md), priorita'
piu' alta del piano, mai risolta prima. L'URL configurato in `config.yaml`
(`arpa_piemonte.url`) risponde 404 da sempre; `ArpaPiemonteDownloader` in
`download_data.py` non ha mai funzionato (nessun endpoint dietro quell'URL) -
lasciato intatto come storico, questo script lo sostituisce per la
validazione ARPA.

API reale trovata via ricerca web il 2026-07-18 (non linkata da nessuna
pagina pubblica del sito ARPA): `utility.arpa.piemonte.it/meteoidro/`,
Django REST Framework, pubblica e senza chiave. Endpoint usati:
- `stazione_meteorologica/` - anagrafica stazioni (`codice_istat_comune`,
  quota, sensori con relative date di attivita').
- `dati_giornalieri_meteo/?fk_id_punto_misura_meteo=<codice>` - dati
  giornalieri reali (`tmax`/`tmin`/`tmedia`), JSON paginato.

Gotcha verificati empiricamente prima di scrivere questo script (non
documentati dall'API):
- I parametri con nome intuitivo `data_after`/`data_before` vengono ignorati
  **silenziosamente** (nessun errore, restituiscono l'intera serie storica
  della stazione) - i parametri di filtro corretti sono `data_min`/`data_max`.
- `page_size` viene ignorato sull'endpoint `dati_giornalieri_meteo/`: ogni
  pagina restituisce sempre ~366 record, paginazione da seguire via `next`.

Copertura reale (verificata il 2026-07-18): su 177 comuni con temperatura
Open-Meteo, 51 hanno almeno una stazione ARPA attiva con sensore di
temperatura (incluse tutte le 8 capoluogo di provincia) - vedi
wiki/pages/data-sources.md per il dettaglio completo.

Usage:
    python -m src.data_acquisition.download_arpa [--dry-run] [--date-min 2000-01-01]
"""

import argparse
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from sqlalchemy import text

from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://utility.arpa.piemonte.it/meteoidro"
STATIONS_URL = f"{BASE_URL}/stazione_meteorologica/"
DAILY_URL = f"{BASE_URL}/dati_giornalieri_meteo/"

# Nessun limite di rate documentato per questa API (a differenza di
# Open-Meteo, vedi wiki/pages/data-sources.md) - piccola pausa tra le
# richieste per prudenza, non per un limite noto.
REQUEST_DELAY_S = 0.3


def fetch_station_registry() -> list[dict]:
    """Scarica l'intera anagrafica stazioni ARPA (paginata, ~336 stazioni)."""
    stations = []
    url, params = STATIONS_URL, {'page_size': 500}
    while url:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        stations.extend(data['results'])
        url, params = data['next'], None
        if url:
            time.sleep(REQUEST_DELAY_S)
    logger.info(f"Anagrafica ARPA: {len(stations)} stazioni totali")
    return stations


def select_stations_for_municipalities(
    stations: list[dict], municipalities: pd.DataFrame
) -> pd.DataFrame:
    """
    Per ciascun comune gia' coperto da Open-Meteo, trova la stazione ARPA
    attiva (`data_fine` stazione e sensore entrambi `None`) con sensore di
    temperatura (`TERMA`) il cui `codice_istat_comune` corrisponde. Se un
    comune ha piu' stazioni attive (tipico nei comuni alpini estesi, con
    piu' rifugi/quote diverse), sceglie quella con quota piu' vicina a
    `municipalities.elevation_m` (fallback: la piu' storica).
    """
    by_istat: dict[str, list[dict]] = {}
    for station in stations:
        if station['data_fine'] is not None:
            continue
        has_active_temp_sensor = any(
            sensor['id_parametro'] == 'TERMA' and sensor['data_fine'] is None
            for sensor in station.get('sensori_meteo', [])
        )
        if has_active_temp_sensor:
            by_istat.setdefault(station['codice_istat_comune'], []).append(station)

    matched = []
    for row in municipalities.itertuples():
        candidates = by_istat.get(row.istat_code)
        if not candidates:
            continue
        if row.elevation_m is not None and len(candidates) > 1:
            best = min(candidates, key=lambda s: abs(s['quota_stazione'] - row.elevation_m))
        else:
            best = min(candidates, key=lambda s: s['data_inizio'])
        # fk_id_punto_misura_meteo e' un URL tipo '.../punti_misura_meteo/PIE-001272-904/'
        station_code = best['fk_id_punto_misura_meteo'].rstrip('/').rsplit('/', 1)[-1]
        matched.append({
            'municipality_id': row.municipality_id,
            'istat_code': row.istat_code,
            'municipality_name': row.name,
            'station_code': station_code,
            'station_name': best['denominazione'],
            'station_quota': best['quota_stazione'],
        })
    return pd.DataFrame(matched)


def fetch_daily_data(station_code: str, date_min: str = '2000-01-01') -> pd.DataFrame:
    """Scarica tutte le osservazioni giornaliere di una stazione da `date_min` a oggi."""
    records = []
    url: Optional[str] = DAILY_URL
    params = {'fk_id_punto_misura_meteo': station_code, 'data_min': date_min}
    while url:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        records.extend(data['results'])
        url, params = data['next'], None
        if url:
            time.sleep(REQUEST_DELAY_S)
    return pd.DataFrame(records)


def main(date_min: str = '2000-01-01', dry_run: bool = False) -> pd.DataFrame:
    raw_path = Path(config.get('paths.raw_data'))
    raw_path.mkdir(parents=True, exist_ok=True)
    output_file = raw_path / 'arpa_temperature.csv'

    with db_manager.engine.connect() as conn:
        municipalities = pd.read_sql(text("""
            SELECT DISTINCT m.municipality_id, m.istat_code, m.name, m.elevation_m
            FROM municipalities m
            JOIN temperature t ON t.municipality_id = m.municipality_id
        """), conn)

    stations = fetch_station_registry()
    matched = select_stations_for_municipalities(stations, municipalities)
    logger.info(
        f"{len(matched)}/{len(municipalities)} comuni con temperatura Open-Meteo "
        "hanno una stazione ARPA attiva con sensore di temperatura"
    )

    if dry_run:
        return matched

    # Salvataggio incrementale (una stazione alla volta, subito su disco):
    # lezione imparata con Open-Meteo (vedi wiki/pages/data-sources.md) -
    # un'interruzione a meta' non deve far perdere le stazioni gia' scaricate.
    if output_file.exists():
        output_file.unlink()

    total_rows = 0
    for i, row in enumerate(matched.itertuples(), 1):
        logger.info(f"[{i}/{len(matched)}] {row.municipality_name} <- {row.station_name} ({row.station_code})")
        try:
            df = fetch_daily_data(row.station_code, date_min=date_min)
        except requests.RequestException as exc:
            logger.error(f"  fallito {row.station_code}: {exc}")
            continue
        if df.empty:
            logger.warning(f"  nessun dato per {row.station_code}")
            continue
        df['municipality_id'] = row.municipality_id
        df['station_code'] = row.station_code
        df['station_name'] = row.station_name
        df = df[['municipality_id', 'station_code', 'station_name', 'data', 'tmax', 'tmin', 'tmedia']].rename(
            columns={'data': 'date', 'tmax': 'temp_max', 'tmin': 'temp_min', 'tmedia': 'temp_mean'}
        )
        df.to_csv(output_file, mode='a', header=(total_rows == 0), index=False)
        total_rows += len(df)
        time.sleep(REQUEST_DELAY_S)

    logger.success(f"Scaricate {total_rows} righe ARPA per {len(matched)} comuni -> {output_file}")
    return matched


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Solo matching comuni<->stazioni, nessun download')
    parser.add_argument('--date-min', default='2000-01-01', help='Data minima da scaricare (default 2000-01-01)')
    args = parser.parse_args()
    main(date_min=args.date_min, dry_run=args.dry_run)
