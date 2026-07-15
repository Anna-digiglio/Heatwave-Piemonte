"""
trend_analysis.py - Analisi del Trend di Temperatura

Analisi statistica del trend di riscaldamento per comune, sulla serie
annuale di temperatura media (2000-2025).

Metodi:
    - Test di Mann-Kendall: rileva un trend monotono senza assumere
      normalità dei dati (dice SE c'è un trend).
    - Regressione lineare (+ stima di Sen's slope): stima la pendenza del
      trend in °C/anno (dice QUANTO).

Usage:
    python -m src.analysis.trend_analysis
"""

from pathlib import Path

import pandas as pd
import pymannkendall as mk
from scipy import stats

from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_annual_temperature() -> pd.DataFrame:
    """
    Carica la temperatura media annuale per comune dalla vista
    materializzata `kpi_annual_by_municipality`.

    Returns:
        pd.DataFrame: colonne (municipality_name, year, temp_mean_annual)
    """
    query = """
        SELECT m.name AS municipality_name, k.year, k.temp_mean_annual
        FROM kpi_annual_by_municipality k
        JOIN municipalities m ON k.municipality_id = m.municipality_id
        ORDER BY m.name, k.year
    """
    rows = db_manager.execute_query(query)
    df = pd.DataFrame(rows, columns=['municipality_name', 'year', 'temp_mean_annual'])
    logger.info(f"Caricate {len(df)} righe annuali per {df['municipality_name'].nunique()} comuni")
    return df


def mann_kendall_trend(series: pd.Series) -> dict:
    """
    Applica il test di Mann-Kendall a una serie annuale.

    Args:
        series (pd.Series): valori ordinati per anno

    Returns:
        dict: trend ('increasing'/'decreasing'/'no trend'), p-value,
        Sen's slope (°C/anno)
    """
    result = mk.original_test(series)
    return {
        'mk_trend': result.trend,
        'mk_p_value': result.p,
        'mk_sen_slope': result.slope,
    }


def linear_trend(years: pd.Series, values: pd.Series) -> dict:
    """
    Regressione lineare della temperatura media annuale nel tempo.

    Args:
        years (pd.Series): anni
        values (pd.Series): temperatura media annuale

    Returns:
        dict: pendenza (°C/anno), pendenza per decade, p-value, r²
    """
    reg = stats.linregress(years, values)
    return {
        'lr_slope_per_year': reg.slope,
        'lr_slope_per_decade': reg.slope * 10,
        'lr_p_value': reg.pvalue,
        'lr_r_squared': reg.rvalue ** 2,
    }


def analyze_all_municipalities() -> pd.DataFrame:
    """
    Esegue Mann-Kendall + regressione lineare per ciascun comune.

    Returns:
        pd.DataFrame: una riga per comune con i risultati di entrambi i test
    """
    df = load_annual_temperature()
    results = []

    for name, group in df.groupby('municipality_name'):
        group = group.sort_values('year')
        n_years = len(group)

        row = {'municipality_name': name, 'n_years': n_years}
        row.update(mann_kendall_trend(group['temp_mean_annual']))
        row.update(linear_trend(group['year'], group['temp_mean_annual']))
        results.append(row)

    result_df = pd.DataFrame(results).sort_values('municipality_name').reset_index(drop=True)
    return result_df


def save_results(df: pd.DataFrame, filename: str = 'trend_analysis.csv') -> Path:
    """Salva i risultati in `output/`."""
    output_path = Path(config.get('paths.output')) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"✓ Risultati salvati: {output_path}")
    return output_path


def main():
    logger.info("=" * 70)
    logger.info("ANALISI TREND DI TEMPERATURA (Mann-Kendall + regressione lineare)")
    logger.info("=" * 70)

    results = analyze_all_municipalities()
    save_results(results)

    for _, row in results.iterrows():
        logger.info(
            f"{row['municipality_name']:25s} "
            f"MK={row['mk_trend']:12s} (p={row['mk_p_value']:.4f}) | "
            f"trend={row['lr_slope_per_decade']:+.3f} °C/decade "
            f"(p={row['lr_p_value']:.4f}, r²={row['lr_r_squared']:.3f})"
        )

    logger.info("✓ Analisi trend completata")


if __name__ == '__main__':
    main()
