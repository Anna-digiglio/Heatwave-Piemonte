"""Caricamento database PostgreSQL/PostGIS per Heatwave Piemonte."""

import os
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import text

from src.utils.config import config
from src.utils.database import db_manager


class DatabaseLoader:
    """Loader per schema e dati nel database."""

    def __init__(self):
        self.sql_path = Path(__file__).resolve().parents[2] / 'sql' / '01_init_database.sql'
        if not self.sql_path.exists():
            raise FileNotFoundError(f'SQL script non trovato: {self.sql_path}')

    def initialize_schema(self) -> None:
        """Esegue lo script SQL di inizializzazione dello schema."""
        logger.info(f'Inizializzazione schema DB da: {self.sql_path}')
        sql_script = self.sql_path.read_text(encoding='utf-8')

        with db_manager.engine.begin() as conn:
            # Esegue lo script sul cursore DBAPI grezzo, non tramite
            # exec_driver_sql: quest'ultimo passa sempre un dict di parametri
            # (anche vuoto) a psycopg2, che quindi prova a interpretare ogni
            # "%" letterale nello script come segnaposto di parametro
            # (paramstyle pyformat) e fallisce non appena il testo ne
            # contiene uno non riconducibile a un placeholder valido.
            cursor = conn.connection.cursor()
            cursor.execute(sql_script)

        logger.success('Schema database creato/aggiornato con successo')

    def verify_schema(self) -> Optional[dict]:
        """Verifica la presenza delle tabelle principali."""
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('provinces', 'municipalities', 'temperature');"
        try:
            with db_manager.engine.connect() as conn:
                result = conn.execute(text(query)).fetchall()
            tables = [row[0] for row in result]
            logger.info(f'Tabelle trovate: {tables}')
            return {'tables': tables}
        except Exception as exc:
            logger.error(f'Errore verifica schema: {exc}')
            return None

    def insert_municipalities(self, csv_path: Optional[Path] = None) -> int:
        """
        Carica i comuni piemontesi (dati reali ISTAT, vedi
        `IstatGeodataDownloader.download_municipalities`) nella tabella
        `municipalities`, risolvendo `province_id` a partire dal codice
        ISTAT di provincia.
        """
        import pandas as pd

        if csv_path is None:
            csv_path = Path(config.get('paths.external_data')) / 'municipalities.csv'
        if not csv_path.exists():
            raise FileNotFoundError(
                f'{csv_path} non trovato. Esegui prima '
                'IstatGeodataDownloader.download_municipalities().'
            )

        # keep_default_na=False evita che pandas trasformi in NaN il nome del
        # comune "None" (provincia di Torino) o altri valori testuali che
        # coincidono con le stringhe NA di default di pandas.
        df = pd.read_csv(
            csv_path,
            dtype={'istat_code': str, 'province_istat_code': str},
            keep_default_na=False,
            na_values=[''],
        )

        with db_manager.engine.begin() as conn:
            province_rows = conn.execute(text('SELECT province_id, istat_code FROM provinces')).fetchall()
        province_map = {row.istat_code: row.province_id for row in province_rows}

        missing_provinces = set(df['province_istat_code']) - set(province_map)
        if missing_provinces:
            raise ValueError(f'Codici provincia ISTAT non trovati in provinces: {missing_provinces}')

        records = [
            {
                'province_id': province_map[row.province_istat_code],
                'name': row.name,
                'istat_code': row.istat_code,
                'geometry_wkt': row.geometry_wkt,
                'area_km2': row.area_km2,
            }
            for row in df.itertuples(index=False)
        ]

        query = text(
            "INSERT INTO municipalities (province_id, name, istat_code, geometry, area_km2) "
            "VALUES (:province_id, :name, :istat_code, ST_Multi(ST_GeomFromText(:geometry_wkt, 4326)), :area_km2) "
            "ON CONFLICT (istat_code) DO NOTHING"
        )

        with db_manager.engine.begin() as conn:
            conn.execute(query, records)

        logger.success(f'{len(records)} comuni inseriti/aggiornati in municipalities')
        return len(records)

    def insert_sample_province(self) -> None:
        """Inserisce un record di prova nella tabella provinces."""
        query = text(
            "INSERT INTO provinces (name, istat_code, geometry, area_km2, population) "
            "VALUES (:name, :istat_code, ST_SetSRID(ST_Point(:lon, :lat), 4326), :area, :population) "
            "ON CONFLICT (name) DO NOTHING"
        )
        params = {
            'name': 'Test Comune Piemonte',
            'istat_code': '999',
            'lon': 7.6866,
            'lat': 45.0730,
            'area': 10.0,
            'population': 1000,
        }

        with db_manager.engine.begin() as conn:
            conn.execute(query, params)

        logger.success('Record di prova inserito in provinces')


def main():
    loader = DatabaseLoader()
    loader.initialize_schema()
    verification = loader.verify_schema()
    if not verification:
        logger.error('Verifica schema fallita: tabelle mancanti.')
        return

    if 'municipalities' in verification['tables']:
        try:
            loader.insert_municipalities()
        except FileNotFoundError as e:
            logger.warning(str(e))

    logger.info('Caricamento DB completato.')


if __name__ == '__main__':
    main()
