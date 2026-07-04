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
        invalid_range = (\n            (df['temp_min'] < self.TEMP_MIN_VALID) |\n            (df['temp_max'] > self.TEMP_MAX_VALID) |\n            (df['temp_mean'] < self.TEMP_MIN_VALID) |\n            (df['temp_mean'] > self.TEMP_MAX_VALID)\n        )\n        invalid_count = invalid_range.sum()\n        logger.warning(f"Temperature fuori range: {invalid_count}")\n        df.loc[invalid_range, 'quality_flag'] = 2  # Bad quality\n        \n        # Inconsistenze logiche: temp_min > temp_max\n        invalid_logic = df['temp_min'] > df['temp_max']\n        logic_errors = invalid_logic.sum()\n        logger.warning(f"Inconsistenze logiche (min > max): {logic_errors}")\n        df.loc[invalid_logic, 'quality_flag'] = 1  # Suspect\n        \n        self.stats['invalid_temperatures'] = int(invalid_count + logic_errors)\n        return df\n    \n    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:\n        """\n        Gestisce valori mancanti.\n        \n        Args:\n            df (pd.DataFrame): Dataframe\n            \n        Returns:\n            pd.DataFrame: Dataframe con missing values gestiti\n        """\n        logger.info("Gestione valori mancanti...")\n        \n        # Conta missing per colonna\n        missing_counts = df.isnull().sum()\n        logger.info(f"Missing values per colonna:\\n{missing_counts}")\n        \n        # Temperature: interpolazione lineare per piccoli gap\n        if df['temp_mean'].isnull().any():\n            df['temp_mean'] = df.groupby('province')['temp_mean'].transform(\n                lambda x: x.interpolate(method='linear', limit=2)\n            )\n        \n        # Precipitation: fillna con 0 (niente pioggia)\n        df['precipitation'] = df['precipitation'].fillna(0)\n        \n        # Rimuovi righe con temperature critiche mancanti\n        df = df.dropna(subset=['temp_max', 'temp_min'])\n        \n        self.stats['rows_after_missing'] = len(df)\n        logger.info(f"✓ Record dopo gestione missing: {len(df)}")\n        \n        return df\n    \n    def detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:\n        """\n        Identifica outlier con IQR method.\n        \n        Args:\n            df (pd.DataFrame): Dataframe\n            \n        Returns:\n            pd.DataFrame: Dataframe con outlier flag\n        """\n        logger.info("Rilevamento outlier (IQR method)...")\n        \n        for col in ['temp_max', 'temp_min', 'temp_mean']:\n            Q1 = df[col].quantile(0.25)\n            Q3 = df[col].quantile(0.75)\n            IQR = Q3 - Q1\n            \n            lower_bound = Q1 - 1.5 * IQR\n            upper_bound = Q3 + 1.5 * IQR\n            \n            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()\n            logger.info(f"{col}: {outliers} outlier rilevati")\n            \n            # Marca outlier\n            df.loc[\n                (df[col] < lower_bound) | (df[col] > upper_bound),\n                'quality_flag'\n            ] = 1\n        \n        self.stats['outliers_detected'] = df[df['quality_flag'] == 1].shape[0]\n        return df\n    \n    def convert_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:\n        """\n        Converte tipi dati appropriati.\n        \n        Args:\n            df (pd.DataFrame): Dataframe\n            \n        Returns:\n            pd.DataFrame: Dataframe con tipi convertiti\n        """\n        logger.info("Conversione tipi dati...")\n        \n        conversions = {\n            'date': 'datetime64[ns]',\n            'temp_max': 'float32',\n            'temp_min': 'float32',\n            'temp_mean': 'float32',\n            'precipitation': 'float32',\n            'province': 'category',\n            'data_source': 'category',\n            'quality_flag': 'uint8'\n        }\n        \n        for col, dtype in conversions.items():\n            if col in df.columns:\n                try:\n                    df[col] = df[col].astype(dtype)\n                except (ValueError, TypeError) as e:\n                    logger.warning(f"Errore conversione {col}: {e}")\n        \n        logger.info(f"✓ Tipi dati convertiti")\n        return df\n    \n    def apply_quality_flags(self, df: pd.DataFrame) -> pd.DataFrame:\n        """\n        Applica flag di qualità ai dati.\n        \n        Args:\n            df (pd.DataFrame): Dataframe\n            \n        Returns:\n            pd.DataFrame: Dataframe con quality flags\n        """\n        logger.info("Applicazione quality flags...")\n        \n        if 'quality_flag' not in df.columns:\n            df['quality_flag'] = 0\n        \n        # Filtra record con quality_flag >= 2 (bad)\n        bad_records = (df['quality_flag'] >= 2).sum()\n        logger.warning(f"Record con qualità scadente (flag >= 2): {bad_records}")\n        \n        df_clean = df[df['quality_flag'] < 2].copy()\n        logger.info(f"✓ Record finali (qualità accettabile): {len(df_clean)}")\n        \n        self.stats['final_records'] = len(df_clean)\n        return df_clean\n    \n    def generate_report(self) -> None:\n        """Genera report di cleaning."""\n        logger.info("\\n\" + \"=\"*70)\n        logger.info(\"REPORT CLEANING DATI\")\n        logger.info(\"=\"*70)\n        logger.info(f\"Record iniziali: {self.stats.get('initial_records', 0)}\")\n        logger.info(f\"Duplicati rimossi: {self.stats.get('duplicates_removed', 0)}\")\n        logger.info(f\"Temperature non valide: {self.stats.get('invalid_temperatures', 0)}\")\n        logger.info(f\"Outlier rilevati: {self.stats.get('outliers_detected', 0)}\")\n        logger.info(f\"Record finali: {self.stats.get('final_records', 0)}\")\n        \n        if self.stats.get('initial_records'):\n            completeness = (\n                self.stats.get('final_records', 0) /\n                self.stats.get('initial_records', 1) * 100\n            )\n            logger.info(f\"Completezza dati: {completeness:.1f}%\")\n        logger.info(\"=\"*70 + \"\\n\")\n    \n    def clean_data(self, input_path: Path) -> pd.DataFrame:\n        """\n        Pipeline completo di cleaning.\n        \n        Args:\n            input_path (Path): Path file input\n            \n        Returns:\n            pd.DataFrame: Dataframe pulito\n        """\n        logger.info(\"\\n\" + \"=\"*70)\n        logger.info(\"INIZIO CLEANING DATI\")\n        logger.info(\"=\"*70 + \"\\n\")\n        \n        # Load\n        df = self.load_data(input_path)\n        \n        # Clean pipeline\n        df = self.remove_duplicates(df)\n        df = self.handle_missing_values(df)\n        df = self.validate_temperature(df)\n        df = self.detect_outliers(df)\n        df = self.convert_dtypes(df)\n        df = self.apply_quality_flags(df)\n        \n        self.generate_report()\n        return df\n    \n    def save_cleaned_data(self, df: pd.DataFrame, output_filename: str) -> None:\n        """\n        Salva dati puliti in CSV.\n        \n        Args:\n            df (pd.DataFrame): Dataframe\n            output_filename (str): Nome file output\n        """\n        output_path = self.processed_path / output_filename\n        df.to_csv(output_path, index=False)\n        logger.info(f\"✓ Dati puliti salvati: {output_path}\")\n        logger.info(f\"  Dimensione file: {output_path.stat().st_size / 1024 / 1024:.2f} MB\")\n\n\ndef main():\n    """Funzione principale."""\n    parser = argparse.ArgumentParser(\n        description=\"Cleaning e validazione dati temperature\"\n    )\n    parser.add_argument(\n        '--input',\n        type=str,\n        required=True,\n        help='File input'\n    )\n    parser.add_argument(\n        '--output',\n        type=str,\n        default='temperature_clean.csv',\n        help='Nome file output'\n    )\n    \n    args = parser.parse_args()\n    \n    try:\n        cleaner = DataCleaner()\n        df_clean = cleaner.clean_data(Path(args.input))\n        cleaner.save_cleaned_data(df_clean, args.output)\n        logger.info(\"✓ Cleaning completato con successo\")\n    except Exception as e:\n        logger.error(f\"✗ Errore: {e}\")\n        raise\n\n\nif __name__ == \"__main__\":\n    main()\n