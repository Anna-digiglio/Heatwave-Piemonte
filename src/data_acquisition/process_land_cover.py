"""
process_land_cover.py - Calcola % uso del suolo (CORINE Land Cover) per comune.

Popola `municipality_land_cover` (vedi sql/03_land_cover.sql), covariata
esplicativa mancante per il paper scientifico - vedi
wiki/pages/paper-scientifico.md.

Fonte: CORINE Land Cover 2018 vettoriale (Copernicus Land Monitoring
Service), scaricato manualmente dall'utente via "Download by area" (decisione
2026-07-16 di non usare l'API CLMS con token JWT: dataset aggiornato ogni
~6 anni, non serve automazione). File GeoPackage, EPSG:3035 (proiezione
equal-area usata da CLC, mantenuta per calcoli di area corretti - stessa
lezione gia' imparata per municipalities.area_km2, vedi data-sources.md),
52.794 poligoni, campo `Code_18` = codice CLC a 3 cifre.

Metodo: overlay geopandas tra le geometrie comunali (reproiettate in
EPSG:3035 per l'occasione) e i poligoni CLC. Le percentuali sono aggregate
alle 5 categorie di Livello 1 CLC (primo carattere del codice a 3 cifre):
1=Artificiale, 2=Agricolo, 3=Forestale/seminaturale, 4=Zone umide,
5=Corpi idrici. I codici speciali (990/995/999 - non classificato/nodata,
vedi data/external/clc_legend.csv) finiscono in "other".

Usage:
    python -m src.data_acquisition.process_land_cover [--gpkg PATH]
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.utils.database import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

CLC_CRS = "EPSG:3035"

LEVEL1_LABELS = {
    '1': 'urban',
    '2': 'agricultural',
    '3': 'forest_seminatural',
    '4': 'wetland',
    '5': 'water',
}
ALL_CATEGORIES = list(LEVEL1_LABELS.values()) + ['other']


def load_municipalities() -> gpd.GeoDataFrame:
    """Tutti i 1180 comuni, riproiettati in EPSG:3035 (equal-area, come CLC)."""
    query = "SELECT municipality_id, name, geometry FROM municipalities"
    gdf = gpd.read_postgis(query, db_manager.engine, geom_col='geometry', crs='EPSG:4326')
    return gdf.to_crs(CLC_CRS)


def load_clc(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    gdf['level1'] = gdf['Code_18'].astype(str).str[0].map(LEVEL1_LABELS).fillna('other')
    return gdf[['level1', 'geometry']]


def compute_land_cover(municipalities: gpd.GeoDataFrame, clc: gpd.GeoDataFrame) -> pd.DataFrame:
    """Overlay + aggregazione: % area per categoria di Livello 1 per comune."""
    overlay = gpd.overlay(municipalities[['municipality_id', 'geometry']], clc, how='intersection')
    overlay['area_m2'] = overlay.geometry.area

    by_class = overlay.groupby(['municipality_id', 'level1'])['area_m2'].sum().unstack(fill_value=0.0)
    by_class = by_class.reindex(columns=ALL_CATEGORIES, fill_value=0.0)

    total_area = municipalities.set_index('municipality_id').geometry.area
    pct = by_class.div(total_area, axis=0) * 100
    pct = pct.reindex(total_area.index, fill_value=0.0)  # comuni non coperti da CLC (fuori dal ritaglio)

    result = pct.reset_index()
    result['dominant_class'] = pct.idxmax(axis=1).values
    return result


def save_results(df: pd.DataFrame, year: int) -> None:
    for _, row in df.iterrows():
        db_manager.execute_update(
            """
            INSERT INTO municipality_land_cover
                (municipality_id, pct_urban, pct_agricultural, pct_forest_seminatural,
                 pct_wetland, pct_water, pct_other, dominant_class, source_year)
            VALUES (:mid, :urban, :agri, :forest, :wetland, :water, :other, :dominant, :year)
            ON CONFLICT (municipality_id) DO UPDATE SET
                pct_urban = EXCLUDED.pct_urban,
                pct_agricultural = EXCLUDED.pct_agricultural,
                pct_forest_seminatural = EXCLUDED.pct_forest_seminatural,
                pct_wetland = EXCLUDED.pct_wetland,
                pct_water = EXCLUDED.pct_water,
                pct_other = EXCLUDED.pct_other,
                dominant_class = EXCLUDED.dominant_class,
                source_year = EXCLUDED.source_year,
                computed_at = CURRENT_TIMESTAMP
            """,
            {
                'mid': int(row['municipality_id']),
                'urban': float(row['urban']),
                'agri': float(row['agricultural']),
                'forest': float(row['forest_seminatural']),
                'wetland': float(row['wetland']),
                'water': float(row['water']),
                'other': float(row['other']),
                'dominant': row['dominant_class'],
                'year': year,
            },
        )


def main(gpkg_path: str, year: int = 2018):
    logger.info("Carico comuni da PostGIS...")
    municipalities = load_municipalities()
    logger.info(f"  {len(municipalities)} comuni")

    logger.info(f"Carico CORINE Land Cover da {gpkg_path}...")
    clc = load_clc(Path(gpkg_path))
    logger.info(f"  {len(clc)} poligoni CLC")

    logger.info("Calcolo overlay geopandas (puo' richiedere qualche minuto)...")
    result = compute_land_cover(municipalities, clc)

    logger.info("Salvo risultati nel DB...")
    save_results(result, year)
    logger.info(f"Uso del suolo calcolato per {len(result)} comuni.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpkg', default='U2018_CLC2018_V2020_20u1.gpkg')
    parser.add_argument('--year', type=int, default=2018)
    args = parser.parse_args()
    main(args.gpkg, args.year)
