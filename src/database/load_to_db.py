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
            # Usa exec_driver_sql per script multilinea su PostgreSQL
            conn.exec_driver_sql(sql_script)

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
    if verification and 'provinces' in verification['tables']:
        loader.insert_sample_province()
        logger.info('Caricamento DB completato.')
    else:
        logger.error('Verifica schema fallita: tabelle mancanti.')


if __name__ == '__main__':
    main()
