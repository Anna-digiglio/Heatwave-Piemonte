"""
seasonal_analysis.py - Scomposizione Stagionale delle Serie di Temperatura

STL decomposition (Seasonal-Trend decomposition using Loess) sulla serie
giornaliera di temperatura media, per isolare il trend di riscaldamento
dalla normale variazione stagionale (estate/inverno).

Usage:
    python -m src.analysis.seasonal_analysis
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from statsmodels.tsa.seasonal import STL

from src.utils.config import config
from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Un anno di dati giornalieri: periodicità stagionale attesa
SEASONAL_PERIOD_DAYS = 365


def load_daily_series(municipality_name: str) -> pd.Series:
    """
    Carica la serie giornaliera di temp_mean per un comune, come Series
    con DatetimeIndex a frequenza giornaliera.

    Args:
        municipality_name (str): nome del comune

    Returns:
        pd.Series: temp_mean indicizzata per data
    """
    query = text("""
        SELECT t.date, t.temp_mean
        FROM temperature t
        JOIN municipalities m ON t.municipality_id = m.municipality_id
        WHERE m.name = :name
        ORDER BY t.date
    """)
    with db_manager.engine.connect() as conn:
        rows = conn.execute(query, {'name': municipality_name}).fetchall()
    df = pd.DataFrame(rows, columns=['date', 'temp_mean'])
    df['date'] = pd.to_datetime(df['date'])
    series = df.set_index('date')['temp_mean'].asfreq('D')

    n_missing = series.isna().sum()
    if n_missing:
        logger.warning(f"{municipality_name}: {n_missing} giorni mancanti, interpolati linearmente")
        series = series.interpolate(method='linear')

    return series


def decompose(series: pd.Series) -> pd.DataFrame:
    """
    Applica STL decomposition e restituisce trend/seasonal/residuo.

    Args:
        series (pd.Series): serie giornaliera continua

    Returns:
        pd.DataFrame: colonne (observed, trend, seasonal, resid)
    """
    stl = STL(series, period=SEASONAL_PERIOD_DAYS, robust=True)
    result = stl.fit()
    return pd.DataFrame({
        'observed': series,
        'trend': result.trend,
        'seasonal': result.seasonal,
        'resid': result.resid,
    })


def summarize_trend_component(decomposed: pd.DataFrame) -> dict:
    """
    Sintetizza la componente di trend STL: variazione totale nel periodo
    e ampiezza stagionale (range della componente seasonal).
    """
    trend = decomposed['trend']
    return {
        'trend_start': round(trend.iloc[:365].mean(), 2),
        'trend_end': round(trend.iloc[-365:].mean(), 2),
        'trend_change_total': round(trend.iloc[-365:].mean() - trend.iloc[:365].mean(), 2),
        'seasonal_amplitude': round(decomposed['seasonal'].max() - decomposed['seasonal'].min(), 2),
    }


def analyze_all_municipalities() -> pd.DataFrame:
    """Esegue la STL decomposition per tutti i comuni con dati reali."""
    query = "SELECT DISTINCT m.name FROM temperature t JOIN municipalities m ON t.municipality_id = m.municipality_id ORDER BY m.name"
    names = [row[0] for row in db_manager.execute_query(query)]

    summaries = []
    output_dir = Path(config.get('paths.output')) / 'seasonal_decomposition'
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in names:
        series = load_daily_series(name)
        decomposed = decompose(series)

        decomposed.to_csv(output_dir / f'{name.lower()}_stl.csv')

        summary = {'municipality_name': name}
        summary.update(summarize_trend_component(decomposed))
        summaries.append(summary)

        logger.info(f"✓ STL completata per {name}")

    return pd.DataFrame(summaries)


def main():
    logger.info("=" * 70)
    logger.info("STL DECOMPOSITION (trend/stagionalità/residuo)")
    logger.info("=" * 70)

    summary = analyze_all_municipalities()

    output_path = Path(config.get('paths.output')) / 'seasonal_trend_summary.csv'
    summary.to_csv(output_path, index=False)

    for _, row in summary.iterrows():
        logger.info(
            f"{row['municipality_name']:15s} "
            f"trend: {row['trend_start']:.1f}°C → {row['trend_end']:.1f}°C "
            f"({row['trend_change_total']:+.2f}°C) | "
            f"ampiezza stagionale: {row['seasonal_amplitude']:.1f}°C"
        )

    logger.info(f"✓ Riepilogo salvato: {output_path}")
    logger.info("✓ Analisi stagionale completata")


if __name__ == '__main__':
    main()
