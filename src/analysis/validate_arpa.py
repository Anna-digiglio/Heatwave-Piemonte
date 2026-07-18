"""
validate_arpa.py - Validazione delle temperature Open-Meteo contro
osservazioni di stazione reali ARPA Piemonte.

Contesto: fase 1 del piano paper (wiki/pages/paper-scientifico.md). Le
temperature in `temperature` sono dati di rianalisi/modello (Open-Meteo), non
osservazioni dirette - un revisore lo contesterebbe per primo. Questo modulo
confronta, per i comuni dove esiste una stazione ARPA reale (vedi
`src/data_acquisition/download_arpa.py`), le due serie sullo stesso
(comune, data) e calcola bias/RMSE/correlazione.

Usage:
    python -m src.analysis.validate_arpa
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_paired_temperatures() -> pd.DataFrame:
    """
    Carica, per i soli comuni con una stazione ARPA corrispondente, le
    coppie (temp_max/temp_min/temp_mean Open-Meteo, temp_max/temp_min/temp_mean
    ARPA) sulla stessa data.

    Returns:
        pd.DataFrame: una riga per (comune, data) con entrambe le serie.
    """
    query = """
        SELECT
            m.municipality_id,
            m.name AS municipality_name,
            t.date,
            t.temp_max AS om_temp_max,
            t.temp_min AS om_temp_min,
            t.temp_mean AS om_temp_mean,
            a.temp_max AS arpa_temp_max,
            a.temp_min AS arpa_temp_min,
            a.temp_mean AS arpa_temp_mean,
            a.station_name
        FROM temperature t
        JOIN arpa_temperature a
            ON a.municipality_id = t.municipality_id AND a.date = t.date
        JOIN municipalities m ON m.municipality_id = t.municipality_id
        ORDER BY m.name, t.date
    """
    rows = db_manager.execute_query(query)
    df = pd.DataFrame(rows, columns=[
        'municipality_id', 'municipality_name', 'date',
        'om_temp_max', 'om_temp_min', 'om_temp_mean',
        'arpa_temp_max', 'arpa_temp_min', 'arpa_temp_mean', 'station_name',
    ])
    logger.info(
        f"Coppie di osservazioni caricate: {len(df)} giorni, "
        f"{df['municipality_name'].nunique()} comuni con stazione ARPA"
    )
    return df


def validation_metrics(observed: pd.Series, reference: pd.Series) -> dict:
    """
    Metriche di validazione di `observed` (Open-Meteo) contro `reference`
    (ARPA, trattata come verita' di terra) su coppie non-null.

    Returns:
        dict: n, bias medio (observed - reference), MAE, RMSE, correlazione
        di Pearson (r, p-value).
    """
    paired = pd.DataFrame({'observed': observed, 'reference': reference}).dropna()
    if len(paired) < 2:
        return {'n_days': len(paired), 'bias': np.nan, 'mae': np.nan, 'rmse': np.nan, 'r': np.nan, 'r_p_value': np.nan}

    diff = paired['observed'] - paired['reference']
    r, p_value = stats.pearsonr(paired['observed'], paired['reference'])
    return {
        'n_days': len(paired),
        'bias': diff.mean(),
        'mae': diff.abs().mean(),
        'rmse': np.sqrt((diff ** 2).mean()),
        'r': r,
        'r_p_value': p_value,
    }


def validate_all_municipalities(paired: pd.DataFrame) -> pd.DataFrame:
    """Calcola le metriche di validazione (su temp_max/temp_min/temp_mean) per ciascun comune."""
    results = []
    for name, group in paired.groupby('municipality_name'):
        row = {'municipality_name': name, 'station_name': group['station_name'].iloc[0]}
        for var in ('temp_max', 'temp_min', 'temp_mean'):
            metrics = validation_metrics(group[f'om_{var}'], group[f'arpa_{var}'])
            row.update({f'{var}_{k}': v for k, v in metrics.items()})
        results.append(row)
    return pd.DataFrame(results).sort_values('municipality_name').reset_index(drop=True)


def save_results(df: pd.DataFrame, filename: str = 'arpa_validation.csv') -> Path:
    """Salva i risultati in `output/`."""
    output_path = Path(config.get('paths.output')) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"✓ Risultati salvati: {output_path}")
    return output_path


def main():
    logger.info("=" * 70)
    logger.info("VALIDAZIONE OPEN-METEO vs ARPA PIEMONTE (dati di stazione reali)")
    logger.info("=" * 70)

    paired = load_paired_temperatures()
    if paired.empty:
        logger.error("Nessuna coppia di osservazioni trovata - arpa_temperature e' vuota?")
        return

    results = validate_all_municipalities(paired)
    save_results(results)

    logger.info(f"\nRiepilogo per comune (bias/RMSE su temp_max, °C):")
    for _, row in results.iterrows():
        logger.info(
            f"{row['municipality_name']:25s} n={row['temp_max_n_days']:5.0f}  "
            f"bias={row['temp_max_bias']:+.2f}  rmse={row['temp_max_rmse']:.2f}  "
            f"r={row['temp_max_r']:.3f}"
        )

    logger.info("\nAggregato su tutti i comuni (temp_max):")
    logger.info(f"  bias medio:  {results['temp_max_bias'].mean():+.2f} °C")
    logger.info(f"  MAE medio:   {results['temp_max_mae'].mean():.2f} °C")
    logger.info(f"  RMSE medio:  {results['temp_max_rmse'].mean():.2f} °C")
    logger.info(f"  r medio:     {results['temp_max_r'].mean():.3f}")

    logger.info("✓ Validazione ARPA completata")


if __name__ == '__main__':
    main()
