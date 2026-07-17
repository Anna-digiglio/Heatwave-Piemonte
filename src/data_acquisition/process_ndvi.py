"""
process_ndvi.py - Calcola NDVI medio (verde da satellite) per comune.

Popola `municipality_ndvi` (vedi sql/04_ndvi.sql), covariata esplicativa
complementare a `municipality_land_cover` (CORINE) per il paper scientifico -
vedi wiki/pages/paper-scientifico.md. Dove CORINE da' classi discrete di uso
del suolo, l'NDVI da' una misura continua di "quanto verde" c'e' anche
dentro una singola classe (es. un urbano con molti alberi vs uno senza).

Fonte: Copernicus Global Land Service (CGLS) NDVI 300m V3, composito
10-giornaliero, scaricato manualmente dall'utente (decisione 2026-07-17,
stesso pattern low-effort gia' usato per CORINE: niente account/API
Sentinel-2 vero, un prodotto NDVI gia' calcolato via Copernicus Browser/
Data Space Ecosystem). Raster GeoTIFF, EPSG:4326 (grid geografica globale -
diversamente da CLC/EPSG:3035, qui non serve riproiezione per l'area).

Il file e' a 8 bit (DN 0-255): DN 0-250 sono NDVI reale via
`NDVI = DN * 0.004 - 0.08` (range -0.08..0.92); DN 251-255 sono flag
dedicati (251=missing/bad quality, 252=cloud/shadow, 253=snow/ice,
254=sea/water, 255=background/nodata) - esclusi dal calcolo, vedi
`pct_valid_pixels` per sapere quanta area del comune era effettivamente
utilizzabile (basso per comuni con laghi o coperti da nuvole nel
composito scelto).

Zonal stats via rasterstats invece dell'overlay vettoriale usato per CLC
(qui il dato sorgente e' un raster, non poligoni) - approssimazione nota:
a 300m di risoluzione, i comuni molto piccoli possono ricadere su pochi
pixel; `all_touched=True` include anche i pixel solo parzialmente coperti
dal confine comunale per mitigare (non eliminare) il problema.

Usage:
    python -m src.data_acquisition.process_ndvi --raster PATH --period 2026-07-01
"""

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats

from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

DN_SCALE = 0.004
DN_OFFSET = -0.08
DN_MAX_VALID = 250  # DN 0-250 -> NDVI reale; 251-255 sono flag (vedi docstring)

# Bucket descrittivi da ndvi_mean, soglie da letteratura NDVI generica
# (non tarate su Piemonte specificamente - utili per lettura rapida in
# dashboard, il valore continuo ndvi_mean resta il dato primario per
# l'analisi statistica).
VEGETATION_BINS = [
    (-1.01, 0.1, 'no_vegetation'),
    (0.1, 0.3, 'sparse'),
    (0.3, 0.5, 'moderate'),
    (0.5, 0.7, 'dense'),
    (0.7, 1.01, 'very_dense'),
]


def classify(ndvi_mean: float) -> str:
    for lo, hi, label in VEGETATION_BINS:
        if lo <= ndvi_mean < hi:
            return label
    return 'no_vegetation'


def load_municipalities() -> gpd.GeoDataFrame:
    """Tutti i 1180 comuni, in EPSG:4326 (nessuna riproiezione: il raster CGLS e' gia' in 4326)."""
    query = "SELECT municipality_id, name, geometry FROM municipalities"
    return gpd.read_postgis(query, db_manager.engine, geom_col='geometry', crs='EPSG:4326')


def compute_ndvi(municipalities: gpd.GeoDataFrame, raster_path: Path) -> pd.DataFrame:
    with rasterio.open(raster_path) as src:
        dn = src.read(1).astype('float32')
        affine = src.transform
        raster_crs = src.crs

    if raster_crs is not None and str(raster_crs) != str(municipalities.crs):
        municipalities = municipalities.to_crs(raster_crs)

    valid_mask = (dn >= 0) & (dn <= DN_MAX_VALID)
    ndvi = np.where(valid_mask, dn * DN_SCALE + DN_OFFSET, np.nan)

    ndvi_stats = zonal_stats(
        municipalities.geometry, ndvi, affine=affine, nodata=np.nan,
        stats=['mean', 'min', 'max', 'std', 'count'], all_touched=True,
    )
    # Secondo passaggio sul DN grezzo (nodata=None -> conta tutti i pixel
    # intersecati, mascherati o no) per calcolare pct_valid_pixels.
    total_stats = zonal_stats(
        municipalities.geometry, dn, affine=affine, nodata=None,
        stats=['count'], all_touched=True,
    )

    rows = []
    for mid, name, ndvi_s, total_s in zip(
        municipalities['municipality_id'], municipalities['name'], ndvi_stats, total_stats
    ):
        total_px = total_s['count'] or 0
        valid_px = ndvi_s['count'] or 0
        mean = ndvi_s['mean']
        if mean is None or total_px == 0:
            logger.warning(f"{name}: nessun pixel del raster interseca il comune, skip")
            continue
        rows.append({
            'municipality_id': mid,
            'ndvi_mean': mean,
            'ndvi_min': ndvi_s['min'],
            'ndvi_max': ndvi_s['max'],
            'ndvi_stddev': ndvi_s['std'],
            'pct_valid_pixels': 100.0 * valid_px / total_px,
            'vegetation_class': classify(mean),
        })
    return pd.DataFrame(rows)


def save_results(df: pd.DataFrame, acquisition_period: str, source_product: str) -> None:
    for _, row in df.iterrows():
        db_manager.execute_update(
            """
            INSERT INTO municipality_ndvi
                (municipality_id, ndvi_mean, ndvi_min, ndvi_max, ndvi_stddev,
                 pct_valid_pixels, vegetation_class, acquisition_period, source_product)
            VALUES (:mid, :mean, :min, :max, :std, :pct_valid, :veg_class, :period, :source)
            ON CONFLICT (municipality_id) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                ndvi_min = EXCLUDED.ndvi_min,
                ndvi_max = EXCLUDED.ndvi_max,
                ndvi_stddev = EXCLUDED.ndvi_stddev,
                pct_valid_pixels = EXCLUDED.pct_valid_pixels,
                vegetation_class = EXCLUDED.vegetation_class,
                acquisition_period = EXCLUDED.acquisition_period,
                source_product = EXCLUDED.source_product,
                computed_at = CURRENT_TIMESTAMP
            """,
            {
                'mid': int(row['municipality_id']),
                'mean': float(row['ndvi_mean']),
                'min': float(row['ndvi_min']) if pd.notna(row['ndvi_min']) else None,
                'max': float(row['ndvi_max']) if pd.notna(row['ndvi_max']) else None,
                'std': float(row['ndvi_stddev']) if pd.notna(row['ndvi_stddev']) else None,
                'pct_valid': float(row['pct_valid_pixels']),
                'veg_class': row['vegetation_class'],
                'period': acquisition_period,
                'source': source_product,
            },
        )


def main(raster_path: str, acquisition_period: str, source_product: str):
    logger.info("Carico comuni da PostGIS...")
    municipalities = load_municipalities()
    logger.info(f"  {len(municipalities)} comuni")

    logger.info(f"Carico raster NDVI da {raster_path}...")
    result = compute_ndvi(municipalities, Path(raster_path))

    logger.info("Salvo risultati nel DB...")
    save_results(result, acquisition_period, source_product)
    skipped = len(municipalities) - len(result)
    logger.info(f"NDVI calcolato per {len(result)}/{len(municipalities)} comuni.")
    if skipped:
        logger.warning(f"{skipped} comuni fuori dalla copertura del raster (nessun pixel intersecato).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--raster', required=True, help="Path al GeoTIFF NDVI (banda 1 = DN CGLS 0-255)")
    parser.add_argument('--period', required=True, help="Composito 10-giornaliero, es. 2026-07-01")
    parser.add_argument('--source', default='CGLS NDVI 300m V3')
    args = parser.parse_args()
    main(args.raster, args.period, args.source)
