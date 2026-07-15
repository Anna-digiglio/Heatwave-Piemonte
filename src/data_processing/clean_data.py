"""
clean_data.py - Pulizia e Validazione Dati

Script per cleaning, validazione e preprocessing dati temperature.

Operations:
    - Rimozione duplicati
    - Gestione valori mancanti
    - Outlier detection (IQR method)
    - Validazione range temperatura
    - Conversione tipi dati

Usage:
    python src/data_processing/clean_data.py --input data/raw/temperature_data.csv
"""

import argparse
from pathlib import Path
from typing import Tuple
import pandas as pd
import numpy as np

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """Cleaner per dati temperature."""

    # Constraint temperature valide (°C)
    TEMP_MIN_VALID = -50
    TEMP_MAX_VALID = 60

    def __init__(self):
        """Inizializza il cleaner."""
        self.raw_path = Path(config.get('paths.raw_data'))
        self.processed_path = Path(config.get('paths.processed_data'))
        self.processed_path.mkdir(parents=True, exist_ok=True)
        self.stats = {}

    def load_data(self, filepath: Path) -> pd.DataFrame:
        """
        Carica dati da CSV.

        Args:
            filepath (Path): Percorso file

        Returns:
            pd.DataFrame: Dataframe caricato
        """
        logger.info(f"Caricamento dati da {filepath}...")
        df = pd.read_csv(filepath)
        logger.info(f"✓ Caricati {len(df)} record")
        self.stats['initial_records'] = len(df)
        return df

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rimuove record duplicati.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe senza duplicati
        """
        duplicates = df.duplicated(subset=['date', 'province']).sum()
        logger.info(f"Record duplicati trovati: {duplicates}")

        df_clean = df.drop_duplicates(subset=['date', 'province'], keep='first')
        self.stats['duplicates_removed'] = duplicates

        logger.info(f"✓ Record dopo rimozione duplicati: {len(df_clean)}")
        return df_clean

    def validate_temperature(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida valori di temperatura.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe con invalid flag
        """
        logger.info("Validazione temperature...")

        # Valori fuori range
        invalid_range = (
            (df['temp_min'] < self.TEMP_MIN_VALID) |
            (df['temp_max'] > self.TEMP_MAX_VALID) |
            (df['temp_mean'] < self.TEMP_MIN_VALID) |
            (df['temp_mean'] > self.TEMP_MAX_VALID)
        )
        invalid_count = invalid_range.sum()
        logger.warning(f"Temperature fuori range: {invalid_count}")
        df.loc[invalid_range, 'quality_flag'] = 2  # Bad quality

        # Inconsistenze logiche: temp_min > temp_max
        invalid_logic = df['temp_min'] > df['temp_max']
        logic_errors = invalid_logic.sum()
        logger.warning(f"Inconsistenze logiche (min > max): {logic_errors}")
        df.loc[invalid_logic, 'quality_flag'] = 1  # Suspect

        self.stats['invalid_temperatures'] = int(invalid_count + logic_errors)
        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gestisce valori mancanti.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe con missing values gestiti
        """
        logger.info("Gestione valori mancanti...")

        # Conta missing per colonna
        missing_counts = df.isnull().sum()
        logger.info(f"Missing values per colonna:\n{missing_counts}")

        # Temperature: interpolazione lineare per piccoli gap
        if df['temp_mean'].isnull().any():
            df['temp_mean'] = df.groupby('province')['temp_mean'].transform(
                lambda x: x.interpolate(method='linear', limit=2)
            )

        # Precipitation: fillna con 0 (niente pioggia)
        df['precipitation'] = df['precipitation'].fillna(0)

        # Rimuovi righe con temperature critiche mancanti
        df = df.dropna(subset=['temp_max', 'temp_min'])

        self.stats['rows_after_missing'] = len(df)
        logger.info(f"✓ Record dopo gestione missing: {len(df)}")

        return df

    def detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifica outlier con IQR method.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe con outlier flag
        """
        logger.info("Rilevamento outlier (IQR method)...")

        for col in ['temp_max', 'temp_min', 'temp_mean']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            logger.info(f"{col}: {outliers} outlier rilevati")

            # Marca outlier con flag=1 (suspect), ma solo se la riga non è
            # già flag=2 (bad, fuori range fisico assegnato da
            # validate_temperature): altrimenti un valore fisicamente
            # impossibile che è anche un outlier IQR verrebbe "declassato"
            # da 2 a 1, sopravvivendo poi ad apply_quality_flags
            # (che scarta solo flag >= 2).
            is_outlier = (df[col] < lower_bound) | (df[col] > upper_bound)
            df.loc[is_outlier & (df['quality_flag'] < 2), 'quality_flag'] = 1

        self.stats['outliers_detected'] = df[df['quality_flag'] == 1].shape[0]
        return df

    def convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte tipi dati appropriati.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe con tipi convertiti
        """
        logger.info("Conversione tipi dati...")

        conversions = {
            'date': 'datetime64[ns]',
            'temp_max': 'float32',
            'temp_min': 'float32',
            'temp_mean': 'float32',
            'precipitation': 'float32',
            'province': 'category',
            'data_source': 'category',
            'quality_flag': 'uint8'
        }

        for col, dtype in conversions.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Errore conversione {col}: {e}")

        logger.info(f"✓ Tipi dati convertiti")
        return df

    def apply_quality_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applica flag di qualità ai dati.

        Args:
            df (pd.DataFrame): Dataframe

        Returns:
            pd.DataFrame: Dataframe con quality flags
        """
        logger.info("Applicazione quality flags...")

        if 'quality_flag' not in df.columns:
            df['quality_flag'] = 0

        # Filtra record con quality_flag >= 2 (bad)
        bad_records = (df['quality_flag'] >= 2).sum()
        logger.warning(f"Record con qualità scadente (flag >= 2): {bad_records}")

        df_clean = df[df['quality_flag'] < 2].copy()
        logger.info(f"✓ Record finali (qualità accettabile): {len(df_clean)}")

        self.stats['final_records'] = len(df_clean)
        return df_clean

    def generate_report(self) -> None:
        """Genera report di cleaning."""
        logger.info("\n" + "="*70)
        logger.info("REPORT CLEANING DATI")
        logger.info("="*70)
        logger.info(f"Record iniziali: {self.stats.get('initial_records', 0)}")
        logger.info(f"Duplicati rimossi: {self.stats.get('duplicates_removed', 0)}")
        logger.info(f"Temperature non valide: {self.stats.get('invalid_temperatures', 0)}")
        logger.info(f"Outlier rilevati: {self.stats.get('outliers_detected', 0)}")
        logger.info(f"Record finali: {self.stats.get('final_records', 0)}")

        if self.stats.get('initial_records'):
            completeness = (
                self.stats.get('final_records', 0) /
                self.stats.get('initial_records', 1) * 100
            )
            logger.info(f"Completezza dati: {completeness:.1f}%")
        logger.info("="*70 + "\n")

    def clean_data(self, input_path: Path) -> pd.DataFrame:
        """
        Pipeline completo di cleaning.

        Args:
            input_path (Path): Path file input

        Returns:
            pd.DataFrame: Dataframe pulito
        """
        logger.info("\n" + "="*70)
        logger.info("INIZIO CLEANING DATI")
        logger.info("="*70 + "\n")

        # Load
        df = self.load_data(input_path)

        # Clean pipeline
        df = self.remove_duplicates(df)
        df = self.handle_missing_values(df)
        # Inizializza quality_flag=0 per tutte le righe PRIMA che
        # validate_temperature/detect_outliers la valorizzino solo per le
        # righe sospette: senza questo, pandas crea la colonna con NaN per
        # le righe non toccate, e apply_quality_flags le scarta tutte
        # (NaN < 2 è False in pandas/numpy).
        df['quality_flag'] = 0
        df = self.validate_temperature(df)
        df = self.detect_outliers(df)
        df = self.convert_dtypes(df)
        df = self.apply_quality_flags(df)

        self.generate_report()
        return df

    def save_cleaned_data(self, df: pd.DataFrame, output_filename: str) -> None:
        """
        Salva dati puliti in CSV.

        Args:
            df (pd.DataFrame): Dataframe
            output_filename (str): Nome file output
        """
        output_path = self.processed_path / output_filename
        df.to_csv(output_path, index=False)
        logger.info(f"✓ Dati puliti salvati: {output_path}")
        logger.info(f"  Dimensione file: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(
        description="Cleaning e validazione dati temperature"
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='File input'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='temperature_clean.csv',
        help='Nome file output'
    )

    args = parser.parse_args()

    try:
        cleaner = DataCleaner()
        df_clean = cleaner.clean_data(Path(args.input))
        cleaner.save_cleaned_data(df_clean, args.output)
        logger.info("✓ Cleaning completato con successo")
    except Exception as e:
        logger.error(f"✗ Errore: {e}")
        raise


if __name__ == "__main__":
    main()
